# Changelog

## 2026-10-17

Presentation and consistency fixes for the Power BI report. KPI thresholds are unchanged. The published `.pbix` is not in this repo; apply `powerbi/DASHBOARD_SPEC.md` in Power BI Desktop.

### Fixed

- **Punctuality totals disagreed across pages because the rates were averaged twice, not because the rule changed.** The executive card (75.01%) is `AVERAGE` of `v_kpi_ops_daily[punctuality_6min]`: each service date counts once. The operations matrix total (0.68) is the station-grain rate (equal-weighted stations, unformatted, so it reads 0.68 rather than 68%). Both are the share of arrival events with `delay_minutes < 6`. `fact_train_runs` has no delay column, so this was not a train-level versus stop-level definition. Measures now divide arrival counts (`punctual arrivals / arrivals`) from `fact_stop_events`, which a date, station, hour, and train-category filter can all slice. The card, the line, and the matrix total match. On one day or one station the value is still the view's rate.
- **The punctuality line covers only a few service dates because that is all the mart contains, not because of a visual filter.** Each ingest requests four hours of `/plan` plus one `/fchg` snapshot. `/fchg` drops trains after they depart and does not backfill. The loader then replaced `stop_events` with `WRITE_TRUNCATE`, so the next run deleted the previous dates. August 8–11 on the published report are the service dates in that snapshot. The line chart hides dates with no rows. Commercial history is regenerated for 90 days every run, which is why revenue and load factor have a long axis.
- Stop-event snapshots are now appended to `rail_ops_raw.stop_events_history` (the latest CSV is still mirrored in `stop_events`). Staging unions both and, when the same stop appears twice, keeps an observed delay over a later plan-only row so a refresh cannot wipe a known delay back to "on time". The first run after deploy copies the current snapshot into history before replacing it.
- The plan hour is taken in Europe/Berlin. The API date/hour is German local time; a UTC clock was requesting the wrong hour.
- The scheduled refresh runs every 3 hours with `--hours 4`, paced under the 60-calls-per-minute API limit. A single 24-hour pull was not used: trains that have not departed yet have no delay and would be stored as on time.
- `v_kpi_route_daily.distance_km` is route length repeated on every route-day. Summing it is what produced "Sum of distance_km". The scatter measure is `Route Distance (km)` (`MAX` per route, blank across routes).
- Load factor and revenue per seat-km totals are ratios of sums (`passengers / seats_total`, `revenue_eur / seat_km`). With a fixed 480 seats per run the load-factor total is the same number as an average of the route-day rates; it stays that way when a slicer drops routes.

### Added

- Short labels on the marts: `dim_station.station_name_short`, `dim_route.origin_short`, `destination_short`, and `route_label` (for example `Karlsruhe – Freiburg` instead of `Freiburg (Breisgau) Hbf`).
- Additive audit columns on the KPI views: `arrival_events`, `punctual_arrivals_6`, `punctual_arrivals_15`, `arrival_delay_minutes`, `cancelled_events`, `platform_changes`, `seats_total`, `seat_km`.
- Filter-context measures: `Active Date Range`, `Slicer Route Label`, `Slicer Station Label`, `Slicer Category Label`, `Filter Summary`.
- Format strings on every measure (percent, thousands separators, EUR). `DASHBOARD_SPEC.md` is now a page-by-page build checklist: titles, fields, axis titles, formats, a 1280×720 grid, and slicers for service date, route, origin, destination, station, and train category, plus the report header.

### Unchanged

- Delay thresholds (`< 6` and `< 16` minutes), the arrival-only punctuality base (cancelled arrivals stay in that base), cancellation rate, per-run load factor, and revenue per seat-km.
- No historical delay backfill. The punctuality axis grows only as scheduled refreshes land after this change.
