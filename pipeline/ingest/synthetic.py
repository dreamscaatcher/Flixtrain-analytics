"""Synthetic commercial overlay: occupancy + revenue per train run.

The DB open API exposes operational data (times, delays, cancellations) but
no commercial data (bookings/revenue). This module generates a clearly
labelled synthetic commercial layer at the train-run grain so occupancy and
revenue KPIs can be modelled and dashboarded honestly (the README and every
doc state which figures are synthetic).

Routes are NOT invented, though: origin, destination, and distance_km below
are loaded from reference/flixtrain_routes.json, which was extracted from
FlixTrain's real, official GTFS feed (see pipeline/ingest/gtfs_routes.py for
the extraction method and full provenance notes). Only seats_sold,
avg_ticket_price_eur, and revenue_eur are generated -- the demand model
below -- since GTFS carries no ridership or pricing data.

Deterministic: same seed -> same output, so tests and demos are reproducible.
Patterns modelled: weekday vs weekend demand, peak-hour uplift, route
popularity, dynamic-pricing-style yield spread.
"""
from __future__ import annotations

import csv
import json
import logging
import random
from datetime import date, timedelta
from pathlib import Path

from pipeline import config

log = logging.getLogger(__name__)

CSV_COLUMNS = [
    "service_date", "train_number", "route_id", "origin", "destination",
    "departure_hour", "seats_total", "seats_sold", "avg_ticket_price_eur",
    "revenue_eur", "distance_km", "is_synthetic",
]

REFERENCE_PATH = Path(__file__).parent / "reference" / "flixtrain_routes.json"


def _load_routes() -> list[tuple[str, str, str, int, float]]:
    """Load real FlixTrain route/distance data (see module docstring)."""
    data = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    return [
        (r["route_id"], r["origin"], r["destination"], r["distance_km"], r["popularity_weight"])
        for r in data["routes"]
    ]


# route_id, origin, destination, km, popularity weight -- real routes/distances,
# modelled popularity (see _load_routes docstring and reference JSON _note field)
ROUTES = _load_routes()

SEATS_PER_TRAIN = 480          # single-deck long-distance consist
DEPARTURES_PER_ROUTE_DAY = 4   # each direction collapsed to route level
DEPARTURE_HOURS = [6, 10, 14, 18]
BASE_PRICE_EUR = 27.0


def _demand_factor(day: date, hour: int, rng: random.Random) -> float:
    weekday = day.weekday()
    f = 1.0
    if weekday >= 5:
        f *= 1.15          # weekend leisure uplift
    if weekday == 4:
        f *= 1.25          # Friday peak
    if hour in (14, 18):
        f *= 1.10          # afternoon/evening preference
    f *= rng.uniform(0.75, 1.15)  # day-to-day noise
    return f


def generate(days: int = 90, end_date: date | None = None,
             out_path: Path | None = None, seed: int = 42) -> Path:
    """Generate `days` days of train-run commercial data ending at `end_date`."""
    rng = random.Random(seed)
    end_date = end_date or date.today()
    out_path = out_path or config.DATA_DIR / "train_runs.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    train_counter = 1200  # FLX-style train numbering
    for d in range(days, 0, -1):
        day = end_date - timedelta(days=d)
        for route_id, origin, dest, km, popularity in ROUTES:
            for i in range(DEPARTURES_PER_ROUTE_DAY):
                hour = DEPARTURE_HOURS[i]
                load = min(0.98, 0.55 * popularity * _demand_factor(day, hour, rng) + 0.15)
                seats_sold = int(SEATS_PER_TRAIN * load)
                # yield rises with load (dynamic-pricing proxy)
                avg_price = round(BASE_PRICE_EUR * (0.7 + 0.9 * load) * (km / 400), 2)
                rows.append({
                    "service_date": day.isoformat(),
                    "train_number": str(train_counter + i * 2),
                    "route_id": route_id,
                    "origin": origin,
                    "destination": dest,
                    "departure_hour": hour,
                    "seats_total": SEATS_PER_TRAIN,
                    "seats_sold": seats_sold,
                    "avg_ticket_price_eur": avg_price,
                    "revenue_eur": round(seats_sold * avg_price, 2),
                    "distance_km": km,
                    "is_synthetic": True,
                })
        train_counter = 1200  # numbering repeats daily, like real schedules

    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    log.info("Generated %s synthetic train runs -> %s", len(rows), out_path)
    return out_path
