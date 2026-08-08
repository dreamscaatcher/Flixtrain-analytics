# KPI Definitions — Single Source of Truth

Every KPI is computed exactly once, in the view listed. Dashboards aggregate; they never re-derive.

## Operational (real data)

**Punctuality 6 min** — `MARTS.V_KPI_OPS_DAILY.PUNCTUALITY_6MIN`
Share of *arrival* events with delay < 6 minutes. Matches Deutsche Bahn's official punctuality definition (a train is "punctual" under 5:59 min delay). Cancelled stops are excluded from the punctuality base and measured separately — hiding cancellations inside punctuality is a classic KPI-gaming trap.

**Punctuality 15 min** — `PUNCTUALITY_15MIN`
Same, threshold < 16 min. The customer-experience view (connection-loss risk).

**Average arrival delay** — `AVG_ARRIVAL_DELAY_MIN`
Mean delay minutes over arrival events. On-time trains count as 0 (delay is never negative in source; early arrivals report no change).

**Cancellation rate** — `CANCELLATION_RATE`
Share of all stop events flagged cancelled (`cs="c"` in the source API).

**Platform-change rate** — `PLATFORM_CHANGE_RATE`
Share of events where the changed platform differs from planned. Operational-friction proxy: platform changes drive missed connections and crowding.

## Commercial (synthetic overlay — labelled)

**Load factor** — `STAGING.STG_TRAIN_RUNS.LOAD_FACTOR`
`seats_sold / seats_total` per run; averaged in `V_KPI_ROUTE_DAILY`.

**Revenue per seat-km** — `REVENUE_PER_SEAT_KM`
`revenue_eur / (seats_total × distance_km)`. The standard rail/airline unit-economics metric: normalizes revenue across routes of different length and capacity. Aggregated as ratio-of-sums (not average-of-ratios) in `V_KPI_ROUTE_DAILY` to avoid Simpson's-paradox distortion.

**Passengers** — `SUM(seats_sold)` per route-day.

## Known limitations

Delay data covers tracked stations only (10 major hubs), so network punctuality is a hub-weighted proxy. The DB API reports changes, not confirmations — an unchanged event is *assumed* on time. Commercial figures are a demand model, not bookings.
