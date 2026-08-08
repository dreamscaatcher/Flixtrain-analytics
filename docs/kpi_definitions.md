# KPI Definitions — Single Source of Truth

Every KPI is computed exactly once, in the view listed. Dashboards aggregate; they never re-derive.

## Operational (real data)

**Punctuality 6 min** — `rail_ops_marts.v_kpi_ops_daily.punctuality_6min`
Share of *arrival* events with delay < 6 minutes. Matches Deutsche Bahn's official punctuality definition (a train is "punctual" under 5:59 min delay). Cancelled stops are excluded from the punctuality base and measured separately — hiding cancellations inside punctuality is a classic KPI-gaming trap.

**Punctuality 15 min** — `punctuality_15min`
Same, threshold < 16 min. The customer-experience view (connection-loss risk).

**Average arrival delay** — `avg_arrival_delay_min`
Mean delay minutes over arrival events. On-time trains count as 0 (delay is never negative in source; early arrivals report no change).

**Cancellation rate** — `cancellation_rate`
Share of all stop events flagged cancelled (`cs="c"` in the source API).

**Platform-change rate** — `platform_change_rate`
Share of events where the changed platform differs from planned. Operational-friction proxy: platform changes drive missed connections and crowding.

## Commercial (real routes, synthetic demand overlay — labelled)

Routes/distances are real (FlixTrain's official GTFS feed); seats sold, pricing, and revenue are a documented synthetic demand model. See `docs/data_dictionary.md` for full provenance.

**Load factor** — `rail_ops_staging.stg_train_runs.load_factor`
`seats_sold / seats_total` per run; averaged in `v_kpi_route_daily`.

**Revenue per seat-km** — `revenue_per_seat_km`
`revenue_eur / (seats_total × distance_km)`. The standard rail/airline unit-economics metric: normalizes revenue across routes of different length and capacity. Aggregated as ratio-of-sums (not average-of-ratios) in `v_kpi_route_daily` to avoid Simpson's-paradox distortion.

**Passengers** — `SUM(seats_sold)` per route-day.

## Known limitations

Delay data covers tracked stations only (10 major hubs), so network punctuality is a hub-weighted proxy. The DB API reports changes, not confirmations — an unchanged event is *assumed* on time. Commercial figures are a demand model, not bookings.
