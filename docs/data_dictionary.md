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

## rail_ops_marts.fact_train_runs — grain: train × route × service date · **route is real, occupancy/revenue is SYNTHETIC**

| Column | Type | Description |
|---|---|---|
| train_run_key | STRING | `date + train + route`, unique |
| date_key / route_key | DATE / STRING | FKs → dim_date, dim_route |
| seats_total / seats_sold | INT64 | capacity 480 (modelled); sold from seeded demand model |
| load_factor | FLOAT64 | sold / total |
| avg_ticket_price_eur / revenue_eur | NUMERIC | yield rises with load (dynamic-pricing proxy) |
| seat_km / revenue_per_seat_km | INT64 / FLOAT64 | unit economics |
| is_synthetic | BOOL | always TRUE — flags the commercial fields only; route/distance are real (see dim_route) |

**Known limitation, found and fixed during QA:** an earlier version of this table attempted to enrich each synthetic run with real delay data via a join on `(train_number, service_date)` against real stop events. That join never matched — verified 0 of 3,600 rows — because synthetic train numbers are always `1200`-`1209` (reset daily), while real DB train numbers use each operator's own numbering (e.g. ICE 857, RE 11441). There is no legitimate way to link a synthetic booking record to a specific real train run; they're separate data domains. The column was removed rather than shipped as a silently-always-NULL field (see `sql/30_marts/20_facts.sql`).

## Dimensions

**dim_date** — calendar 2026–2027, generated in-warehouse; ISO weeks, weekend flag.
**dim_station** — EVA number + name, from observed stop events (real, DB Timetables API). `station_name_short` drops a parenthetical qualifier (`Frankfurt (Main) Hbf` → `Frankfurt Hbf`) for tight labels. `station_name` is the full name.
**dim_route** — 10 real city-pair segments of FlixTrain's actual single operating corridor (Hamburg–Berlin–Erfurt–Frankfurt–Karlsruhe–Freiburg–Basel), with real distances computed from FlixTrain's official GTFS feed. Only `popularity_weight` (used to shape the synthetic demand model) is an estimate — GTFS carries no ridership data. Full provenance: `pipeline/ingest/reference/flixtrain_routes.json`, extraction method in `pipeline/ingest/gtfs_routes.py`. Note: FlixTrain's GTFS also defines two more lines (Hamburg–Köln, Dresden–Berlin–Köln–Aachen) with zero active trips in the current feed — i.e. not currently operated, which is itself a real finding about FlixTrain's present network size, not a data gap. `origin_short` / `destination_short` drop a parenthetical. `route_label` is the legend label: qualifier and a trailing `Hbf` / `Sued` / `Bad Bf` / `Bf` removed, cities joined with " – " (`Karlsruhe – Freiburg`). `origin` and `destination` stay the full GTFS names.
**dim_train** — category (FLX/ICE/IC) + number; `is_flix_train` flag (from real DB Timetables data — FLX trains are relatively rare in this sample since the tracked stations are DB long-distance hubs, not FlixTrain-specific stops).

## KPI view columns added for additive totals

`v_kpi_ops_daily` and `v_kpi_station` still expose the averaged rate columns (`punctuality_6min`, `avg_arrival_delay_min`, `cancellation_rate`, plus `punctuality_15min` and `platform_change_rate` on the daily view). They also expose `arrival_events`, `punctual_arrivals_6`, `arrival_delay_minutes`, `cancelled_events` (and `punctual_arrivals_15`, `platform_changes` on the daily view) so a total can be a ratio of sums. `v_kpi_route_daily` adds `seats_total`, `seat_km`, and `route_label`. `avg_load_factor` on `v_kpi_exec_daily` is passengers ÷ seats for that day.

`v_kpi_station` has no `date_key`. A date slicer does not filter it. The operations page uses the measures on `fact_stop_events` instead.

## RAW layer

`rail_ops_raw.train_runs` mirrors the latest commercial CSV (replaced each run). `rail_ops_raw.stop_events` mirrors the latest timetable CSV. `rail_ops_raw.stop_events_history` appends every timetable snapshot: the Timetables API only returns a near-term window, and replacing `stop_events` was discarding prior service dates. Staging unions history with the latest snapshot and dedupes. No transformation before staging — reprocessing is always possible from landed data.
