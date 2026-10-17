"""Ingest real timetable + delay data from the Deutsche Bahn Timetables API.

API: https://developers.deutschebahn.com (API Marketplace -> Timetables, free tier).
Two endpoints are used:
  /plan/{evaNo}/{YYMMDD}/{HH}  -> planned stops for one station-hour (XML)
  /fchg/{evaNo}                -> all known changes (delays, cancellations) (XML)

The plan date and hour are German local time (Europe/Berlin). One run writes
only that near-term window: /fchg drops a train once it has departed, and it
does not backfill earlier days. Multi-day punctuality comes from retaining
each snapshot in BigQuery (see pipeline.load.bigquery_loader), not from
asking the API for history and not from this CSV, which is always just the
latest window.

Output grain: one row per stop event (train x station x arrival|departure),
with planned and changed timestamps kept separate. Delay minutes are
deliberately NOT computed here -- that happens in SQL staging, so the
warehouse stays the single source of truth for derived logic.

Offline mode: if no API credentials are configured, bundled XML fixtures are
parsed instead, so the full pipeline is runnable and testable without keys.
"""
from __future__ import annotations

import csv
import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator
from zoneinfo import ZoneInfo

import requests

from pipeline import config

log = logging.getLogger(__name__)

BERLIN = ZoneInfo("Europe/Berlin")
# Marketplace free tier: 60 calls per minute. Stay under it on a 10-station pull.
API_PAUSE_SECONDS = 1.1

CSV_COLUMNS = [
    "stop_id", "station_eva", "station_name", "train_category", "train_number",
    "line", "event_type", "planned_time", "changed_time", "planned_platform",
    "changed_platform", "cancelled", "loaded_at",
]


def _headers() -> dict:
    return {
        "DB-Client-Id": config.DB_CLIENT_ID,
        "DB-Api-Key": config.DB_API_KEY,
        "accept": "application/xml",
    }


def _parse_ts(raw: str | None) -> str | None:
    """API timestamps are YYMMDDHHmm -> ISO-8601 (Europe/Berlin local)."""
    if not raw:
        return None
    return datetime.strptime(raw, "%y%m%d%H%M").isoformat()


def parse_timetable_xml(xml_text: str, station_eva: int) -> Iterator[dict]:
    """Parse a /plan or /fchg XML document into stop-event rows.

    Each <s> element is one train stop; <ar>/<dp> children are the
    arrival/departure events with pt (planned) and ct (changed) times.
    """
    root = ET.fromstring(xml_text)
    station_name = root.get("station") or config.STATIONS.get(station_eva, str(station_eva))
    now = datetime.utcnow().isoformat()

    for s in root.iter("s"):
        stop_id = s.get("id", "")
        tl = s.find("tl")  # trip label: category (ICE/IC/FLX...), number, owner
        category = tl.get("c", "") if tl is not None else ""
        number = tl.get("n", "") if tl is not None else ""

        for tag, event_type in (("ar", "ARRIVAL"), ("dp", "DEPARTURE")):
            ev = s.find(tag)
            if ev is None:
                continue
            yield {
                "stop_id": stop_id,
                "station_eva": station_eva,
                "station_name": station_name,
                "train_category": category,
                "train_number": number,
                "line": ev.get("l", ""),
                "event_type": event_type,
                "planned_time": _parse_ts(ev.get("pt")),
                "changed_time": _parse_ts(ev.get("ct")),
                "planned_platform": ev.get("pp", ""),
                "changed_platform": ev.get("cp", ""),
                "cancelled": ev.get("cs", "") == "c",
                "loaded_at": now,
            }


def plan_start(now: datetime | None = None) -> datetime:
    """Naive Europe/Berlin wall time, truncated to the hour, for /plan.

    The API treats YYMMDD/HH as German local time. A UTC `datetime.now()` on
    GitHub Actions requests the wrong hour and, around midnight, the wrong date.
    Aware datetimes are converted. Naive datetimes are treated as already Berlin.
    """
    if now is None:
        now = datetime.now(BERLIN)
    elif now.tzinfo is not None:
        now = now.astimezone(BERLIN)
    return now.replace(minute=0, second=0, microsecond=0, tzinfo=None)


def _get(url: str) -> str:
    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    time.sleep(API_PAUSE_SECONDS)
    return resp.text


def fetch_station_hour(station_eva: int, when: datetime) -> str:
    """GET planned timetable for one station-hour. Returns raw XML."""
    url = f"{config.DB_API_BASE}/plan/{station_eva}/{when:%y%m%d}/{when:%H}"
    return _get(url)


def fetch_changes(station_eva: int) -> str:
    """GET all currently known changes (delays/cancellations) for a station."""
    url = f"{config.DB_API_BASE}/fchg/{station_eva}"
    return _get(url)


def _rows_from_fixtures() -> list[dict]:
    rows: list[dict] = []
    for fixture in sorted(config.FIXTURES_DIR.glob("timetable_*.xml")):
        eva = int(fixture.stem.split("_")[1])
        rows.extend(parse_timetable_xml(fixture.read_text(encoding="utf-8"), eva))
    return rows


def _rows_from_api(hours: int, now: datetime | None = None) -> list[dict]:
    # A wide pull records trains that have not departed yet. /fchg has no delay
    # for them, and staging treats "no change" as on time, which inflates
    # punctuality. Keep the window short and retain each run instead.
    if hours > 6:
        log.warning(
            "hours=%s is wider than the window where delays are already known. "
            "Trains that have not departed are stored as on time. Prefer the "
            "default of 4 and a frequent schedule.",
            hours,
        )
    rows: list[dict] = []
    start = plan_start(now)
    log.info(
        "Plan window starts %s Europe/Berlin for %s hour(s)",
        start.isoformat(timespec="hours"),
        hours,
    )
    for eva in config.STATIONS:
        # planned slices for the next N hours
        for h in range(hours):
            try:
                rows.extend(parse_timetable_xml(fetch_station_hour(eva, start + timedelta(hours=h)), eva))
            except requests.RequestException as exc:
                log.warning("plan fetch failed for %s +%sh: %s", eva, h, exc)
        # current delay/cancellation picture (future and in-progress trains only)
        try:
            rows.extend(parse_timetable_xml(fetch_changes(eva), eva))
        except requests.RequestException as exc:
            log.warning("fchg fetch failed for %s: %s", eva, exc)
    return rows


def ingest(out_path: Path | None = None, hours: int = 4, now: datetime | None = None) -> Path:
    """Run ingestion (API if credentials exist, fixtures otherwise) -> CSV."""
    out_path = out_path or config.DATA_DIR / "stop_events.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if config.DB_CLIENT_ID and config.DB_API_KEY:
        log.info("Ingesting live data from DB Timetables API")
        rows = _rows_from_api(hours, now=now)
    else:
        log.info("No DB API credentials found -> using bundled fixtures (offline mode)")
        rows = _rows_from_fixtures()

    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    log.info("Wrote %s stop events -> %s", len(rows), out_path)
    return out_path
