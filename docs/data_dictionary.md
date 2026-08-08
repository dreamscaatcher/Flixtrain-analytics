# Data Dictionary

## rail_ops_marts.fact_stop_events — grain: train × station × event (arrival/departure)

| Column | Type | Description |
|---|---|---|
| stop_event_key | STRING | `stop_id + event_type`, unique |
| date_key | DATE | FK → dim_date (planned service date) |
| station_key | INT64 | FK → dim_station (EVA number) |
| train_key | STRING | FK → dim_train (`category + number`) |
| event_type | STRING | ARRIVAL / DEPARTURE |
| planned_time / actual_time | DATETIME | Actual = changed time, falls back to planned |
| delay_minutes | INT64 | `actual − planned`, minutes; 0 if no change reported |
| is_punctual_6 / is_punctual_15 | BOOL | delay < 6 / < 16 min |
| cancelled | BOOL | source flag `cs="c"` |
| platform_changed | BOOL | changed platform ≠ planned |
| planned_hour | INT64 | 0–23, for peak-hour analysis |

## rail_ops_marts.fact_train_runs — grain: train × route × service date · **SYNTHETIC commercial layer**

| Column | Type | Description |
|---|---|---|
| train_run_key | STRING | `date + train + route`, unique |
| date_key / route_key | DATE / STRING | FKs → dim_date, dim_route |
| seats_total / seats_sold | INT64 | capacity 480; sold from seeded demand model |
| load_factor | FLOAT64 | sold / total |
| avg_ticket_price_eur / revenue_eur | NUMERIC | yield rises with load (dynamic-pricing proxy) |
| seat_km / revenue_per_seat_km | INT64 / FLOAT64 | unit economics |
| max_arrival_delay | INT64 | enrichment from real stop events, NULL if no match |
| is_synthetic | BOOL | always TRUE — honesty flag |

## Dimensions

**dim_date** — calendar 2026–2027, generated in-warehouse; ISO weeks, weekend flag.
**dim_station** — EVA number + name, from observed stop events.
**dim_route** — origin/destination/distance for the 10 modelled corridors.
**dim_train** — category (FLX/ICE/IC) + number; `is_flix_train` flag.

## RAW layer

Mirrors pipeline CSVs 1:1 (`pipeline/ingest/db_timetables.py` → `rail_ops_raw.stop_events`, `pipeline/ingest/synthetic.py` → `rail_ops_raw.train_runs`). No transformation before staging — reprocessing is always possible from landed data.
