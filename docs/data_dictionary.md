# Data Dictionary

## MARTS.FACT_STOP_EVENTS — grain: train × station × event (arrival/departure)

| Column | Type | Description |
|---|---|---|
| STOP_EVENT_KEY | VARCHAR | `stop_id + event_type`, unique |
| DATE_KEY | DATE | FK → DIM_DATE (planned service date) |
| STATION_KEY | NUMBER | FK → DIM_STATION (EVA number) |
| TRAIN_KEY | VARCHAR | FK → DIM_TRAIN (`category + number`) |
| EVENT_TYPE | VARCHAR | ARRIVAL / DEPARTURE |
| PLANNED_TIME / ACTUAL_TIME | TIMESTAMP_NTZ | Actual = changed time, falls back to planned |
| DELAY_MINUTES | NUMBER | `actual − planned`, minutes; 0 if no change reported |
| IS_PUNCTUAL_6 / IS_PUNCTUAL_15 | BOOLEAN | delay < 6 / < 16 min |
| CANCELLED | BOOLEAN | source flag `cs="c"` |
| PLATFORM_CHANGED | BOOLEAN | changed platform ≠ planned |
| PLANNED_HOUR | NUMBER | 0–23, for peak-hour analysis |

## MARTS.FACT_TRAIN_RUNS — grain: train × route × service date · **SYNTHETIC commercial layer**

| Column | Type | Description |
|---|---|---|
| TRAIN_RUN_KEY | VARCHAR | `date + train + route`, unique |
| DATE_KEY / ROUTE_KEY | DATE / VARCHAR | FKs → DIM_DATE, DIM_ROUTE |
| SEATS_TOTAL / SEATS_SOLD | NUMBER | capacity 480; sold from seeded demand model |
| LOAD_FACTOR | NUMBER | sold / total |
| AVG_TICKET_PRICE_EUR / REVENUE_EUR | NUMBER | yield rises with load (dynamic-pricing proxy) |
| SEAT_KM / REVENUE_PER_SEAT_KM | NUMBER | unit economics |
| MAX_ARRIVAL_DELAY | NUMBER | enrichment from real stop events, NULL if no match |
| IS_SYNTHETIC | BOOLEAN | always TRUE — honesty flag |

## Dimensions

**DIM_DATE** — calendar 2026–2027, generated in-warehouse; ISO weeks, weekend flag.
**DIM_STATION** — EVA number + name, from observed stop events.
**DIM_ROUTE** — origin/destination/distance for the 10 modelled corridors.
**DIM_TRAIN** — category (FLX/ICE/IC) + number; `IS_FLIX_TRAIN` flag.

## RAW layer

Mirrors pipeline CSVs 1:1 (`pipeline/ingest/db_timetables.py` → `RAW.STOP_EVENTS`, `pipeline/ingest/synthetic.py` → `RAW.TRAIN_RUNS`). No transformation before STAGING — reprocessing is always possible from landed data.
