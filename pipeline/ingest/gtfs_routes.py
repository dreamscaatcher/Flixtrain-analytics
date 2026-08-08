"""One-off extraction tool: derive real FlixTrain route/distance data from
the official FlixTrain GTFS feed.

This is NOT called by the main pipeline (pipeline.run_pipeline). Downloading
and parsing a 30+ MB GTFS zip on every run would break the offline-first,
fast-test design of this project. Instead this script is run manually,
occasionally, to regenerate reference/flixtrain_routes.json, which IS what
synthetic.py loads at runtime (small, static, checked into git, fully
offline).

Re-run this if FlixTrain's real network changes (new lines, retired lines):

    python -m pipeline.ingest.gtfs_routes

Source: official FlixTrain GTFS feed, published by Flix SE and mirrored on
France's national transport open-data portal (transport.data.gouv.fr,
dataset "Reseau europeen FlixBus et FlixTrain").
"""
from __future__ import annotations

import csv
import io
import json
import logging
import math
import zipfile
from collections import defaultdict
from pathlib import Path

import requests

from pipeline import config

log = logging.getLogger(__name__)

GTFS_URL = "https://gtfs.gis.flix.tech/gtfs_generic_eu.zip"
OUT_PATH = Path(__file__).parent / "reference" / "flixtrain_routes.json"


def _haversine(a: tuple[float, float], b: tuple[float, float]) -> int:
    lat1, lon1 = a
    lat2, lon2 = b
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    x = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(x)))


def find_rail_routes(zf: zipfile.ZipFile) -> list[str]:
    """Return route_ids where agency is FlixTrain and route_type is rail (2)."""
    rail = []
    with zf.open("routes.txt") as f:
        for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8")):
            if row["agency_id"] == "FLIXTRAIN-eu" and row["route_type"] == "2":
                rail.append(row["route_id"])
    return rail


def longest_trip_pattern(zf: zipfile.ZipFile, route_id: str) -> list[dict]:
    """Return the full ordered real stop sequence for a route's longest trip."""
    trip_ids = set()
    with zf.open("trips.txt") as f:
        for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8")):
            if row["route_id"] == route_id:
                trip_ids.add(row["trip_id"])

    by_trip = defaultdict(list)
    with zf.open("stop_times.txt") as f:
        for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8")):
            if row["trip_id"] in trip_ids:
                by_trip[row["trip_id"]].append(row)

    if not by_trip:
        return []
    longest = max(by_trip, key=lambda t: len(by_trip[t]))
    return sorted(by_trip[longest], key=lambda r: int(r["stop_sequence"]))


def stop_coords(zf: zipfile.ZipFile) -> dict[str, tuple[str, float, float]]:
    coords = {}
    with zf.open("stops.txt") as f:
        for row in csv.DictReader(io.TextIOWrapper(f, encoding="utf-8")):
            coords[row["stop_id"]] = (row["stop_name"], float(row["stop_lat"]), float(row["stop_lon"]))
    return coords


def main() -> None:
    """Download the feed and report the real rail network -- prints findings
    for manual review; does NOT auto-write the reference JSON, since the
    choice of which city-pair segments to model as 'routes' from the raw
    stop sequence is an editorial decision worth a human look, not something
    to silently overwrite on every run.
    """
    log.info("Downloading %s", GTFS_URL)
    resp = requests.get(GTFS_URL, timeout=120)
    resp.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(resp.content))

    rail_routes = find_rail_routes(zf)
    log.info("FlixTrain rail routes defined: %s", rail_routes)

    coords = stop_coords(zf)
    for route_id in rail_routes:
        seq = longest_trip_pattern(zf, route_id)
        if not seq:
            log.info("%s: no active trips in this GTFS snapshot", route_id)
            continue
        log.info("%s: %s real stops, %s -> %s", route_id, len(seq),
                  coords[seq[0]["stop_id"]][0], coords[seq[-1]["stop_id"]][0])
        for row in seq:
            name = coords[row["stop_id"]][0]
            log.info("    %s  %s", row.get("departure_time", ""), name)

    log.info("Reference file to hand-curate from this output: %s", OUT_PATH)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
