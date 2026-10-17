# KPI Definitions — Single Source of Truth

Every KPI rule is computed exactly once, in SQL. Dashboards aggregate those columns. They never re-derive a threshold or a ratio.

## Operational (real data)

**Punctuality 6 min** — `fact_stop_events.is_punctual_6`, rate at day grain in `v_kpi_ops_daily.punctuality_6min`
Share of *arrival* events with delay < 6 minutes. Matches Deutsche Bahn's official punctuality threshold (a train is "punctual" under 5:59 min delay). The implemented base is every arrival event, including cancelled arrivals: `is_punctual_6` is `delay_minutes < 6` with no cancellation filter. Cancellation rate is the separate KPI beside it. (A cancelled arrival with no changed time has delay 0 and counts as punctual. That predicate was not changed.)

**Punctuality 15 min** — `punctuality_15min` / `is_punctual_15`
Same base, threshold < 16 min. The customer-experience view (connection-loss risk).

**Average arrival delay** — `avg_arrival_delay_min`
Mean delay minutes over arrival events. On-time trains count as 0 (delay is never negative in source; early arrivals report no change).

**Cancellation rate** — `cancellation_rate`
Share of all stop events flagged cancelled (`cs="c"` in the source API).

**Platform-change rate** — `platform_change_rate`
Share of events where the changed platform differs from planned. Operational-friction proxy: platform changes drive missed connections and crowding.

## Commercial (real routes, synthetic demand overlay — labelled)

Routes/distances are real (FlixTrain's official GTFS feed); seats sold, pricing, and revenue are a documented synthetic demand model. See `docs/data_dictionary.md` for full provenance.

**Load factor** — `rail_ops_staging.stg_train_runs.load_factor`
`seats_sold / seats_total` per run. `v_kpi_route_daily.avg_load_factor` is the unweighted mean of those run-level ratios on one route-day (equal to passengers ÷ seats while every run has the same 480 seats). The dashboard measure is `SUM(passengers) / SUM(seats_total)` so a total across routes and days stays the ratio of sums.

**Revenue per seat-km** — `revenue_per_seat_km`
`revenue_eur / (seats_total × distance_km)`. The standard rail/airline unit-economics metric: normalizes revenue across routes of different length and capacity. Aggregated as ratio-of-sums (not average-of-ratios) in `v_kpi_route_daily` to avoid Simpson's-paradox distortion.

**Passengers** — `SUM(seats_sold)` per route-day.

## Aggregation

Rate columns on the KPI views are already averaged at that view's grain. They are the right number for one day or one station. They are not additive:

- Averaging `v_kpi_ops_daily.punctuality_6min` across days weights each day equally. That is the published executive card, 75.01%: the unweighted mean of the daily rates drawn on the line.
- Averaging `v_kpi_station.punctuality_6min` across stations weights each station equally. That is the published operations total, 0.68, shown as a decimal because the column has no percent format.

Those are not two punctuality definitions, and not stop-level versus train-level. `fact_train_runs` has no delay columns. Both figures are the arrival-event rule above, totaled in a way that does not recombine. The dashboard measures divide the additive columns (`punctual_arrivals_6 / arrival_events`, `arrival_delay_minutes / arrival_events`, `passengers / seats_total`, `revenue_eur / seat_km`) so the card, the by-date line, and the station-matrix total are the same ratio under the same slicers. At a single day or a single station, punctuality still equals the view's rate column.

`distance_km` on `v_kpi_route_daily` is the route length repeated once per route-day. Summing it multiplies kilometres by the number of days. Use `MAX` per route (`Route Distance (km)` in `powerbi/measures.dax`).

## Known limitations

Delay data covers tracked stations only (10 major hubs), so network punctuality is a hub-weighted proxy. The DB API reports changes, not confirmations — an unchanged event is *assumed* on time. Commercial figures are a demand model, not bookings.

Real per-run delay cannot currently be joined to synthetic bookings: synthetic train numbers (`1200`-`1209`, reset daily) and real DB train numbers (each operator's own numbering) are unrelated ID spaces, so no legitimate join key exists between them. An earlier version of `fact_train_runs` attempted this join and always returned NULL (verified: 0 of 3,600 rows matched) — removed rather than shipped silently broken. `v_kpi_route_daily` carries route `distance_km` instead, to support demand-vs-distance analysis without a false real/synthetic linkage.
