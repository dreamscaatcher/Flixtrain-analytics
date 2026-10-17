-- KPI views: the ONLY layer BI tools read. Definitions live here, once.
-- Full business definitions: docs/kpi_definitions.md
--
-- Rate columns (punctuality_6min, avg_arrival_delay_min, cancellation_rate,
-- avg_load_factor, ...) are already averaged at this view's grain. They are
-- correct for a single row. Do not average or sum them across rows in a BI
-- tool: that is a different total (equal-weighted days, or equal-weighted
-- stations) and it will not match the event-weighted measures in
-- powerbi/measures.dax. The count and sum columns below are the additive
-- pieces those measures use. Thresholds are not restated there.

-- Daily operational KPIs (real data). One row per service date.
CREATE OR REPLACE VIEW rail_ops_marts.v_kpi_ops_daily AS
SELECT
  date_key,
  COUNT(*)                                                    AS stop_events,
  COUNT(DISTINCT train_key)                                   AS trains,
  COUNTIF(event_type = 'ARRIVAL')                             AS arrival_events,
  COUNTIF(event_type = 'ARRIVAL' AND is_punctual_6)           AS punctual_arrivals_6,
  COUNTIF(event_type = 'ARRIVAL' AND is_punctual_15)          AS punctual_arrivals_15,
  SUM(IF(event_type = 'ARRIVAL', delay_minutes, NULL))        AS arrival_delay_minutes,
  AVG(IF(event_type = 'ARRIVAL', delay_minutes, NULL))        AS avg_arrival_delay_min,
  AVG(IF(event_type = 'ARRIVAL',
         IF(is_punctual_6, 1, 0), NULL))                      AS punctuality_6min,
  AVG(IF(event_type = 'ARRIVAL',
         IF(is_punctual_15, 1, 0), NULL))                     AS punctuality_15min,
  COUNTIF(cancelled)                                          AS cancelled_events,
  AVG(IF(cancelled, 1, 0))                                    AS cancellation_rate,
  COUNTIF(platform_changed)                                   AS platform_changes,
  AVG(IF(platform_changed, 1, 0))                             AS platform_change_rate
FROM rail_ops_marts.fact_stop_events
GROUP BY date_key;

-- Station-level delay picture (real data), all dates combined.
-- Not date-filterable: there is no date_key. The dashboard matrix must use
-- the measures on fact_stop_events so the date slicer applies. Averaging
-- punctuality_6min across these rows is the equal-weighted station mean,
-- not the network rate.
CREATE OR REPLACE VIEW rail_ops_marts.v_kpi_station AS
SELECT
  f.station_key,
  s.station_name,
  s.station_name_short,
  COUNT(*)                                                    AS stop_events,
  COUNTIF(f.event_type = 'ARRIVAL')                           AS arrival_events,
  COUNTIF(f.event_type = 'ARRIVAL' AND f.is_punctual_6)       AS punctual_arrivals_6,
  SUM(IF(f.event_type = 'ARRIVAL', f.delay_minutes, NULL))    AS arrival_delay_minutes,
  AVG(IF(f.event_type = 'ARRIVAL', f.delay_minutes, NULL))    AS avg_arrival_delay_min,
  AVG(IF(f.event_type = 'ARRIVAL',
         IF(f.is_punctual_6, 1, 0), NULL))                    AS punctuality_6min,
  COUNTIF(f.cancelled)                                        AS cancelled_events,
  AVG(IF(f.cancelled, 1, 0))                                  AS cancellation_rate
FROM rail_ops_marts.fact_stop_events f
JOIN rail_ops_marts.dim_station s ON s.station_key = f.station_key
GROUP BY 1, 2, 3;

-- Route-level commercial KPIs (synthetic overlay), daily.
-- distance_km is the route length, constant per route_key, repeated on every
-- route-day. Summing it multiplies length by the number of days. The
-- dashboard measure takes MAX. avg_load_factor is the unweighted mean of
-- run-level load factors on that route-day (equal to passengers/seats while
-- every run has the same seat count). Cross-day totals use passengers and
-- seats_total, not an average of avg_load_factor.
CREATE OR REPLACE VIEW rail_ops_marts.v_kpi_route_daily AS
SELECT
  f.date_key,
  f.route_key,
  r.origin,
  r.destination,
  MAX(r.route_label)                                          AS route_label,
  COUNT(*)                                                    AS train_runs,
  SUM(f.seats_sold)                                           AS passengers,
  SUM(f.seats_total)                                          AS seats_total,
  AVG(f.load_factor)                                          AS avg_load_factor,
  SUM(f.revenue_eur)                                          AS revenue_eur,
  SUM(f.seat_km)                                              AS seat_km,
  SAFE_DIVIDE(SUM(f.revenue_eur), SUM(f.seat_km))             AS revenue_per_seat_km,
  MAX(r.distance_km)                                          AS distance_km
FROM rail_ops_marts.fact_train_runs f
JOIN rail_ops_marts.dim_route r ON r.route_key = f.route_key
GROUP BY 1, 2, 3, 4;

-- Executive daily rollup: ops + commercial in one row per day.
-- avg_load_factor here is passengers / seats for that day (ratio of sums),
-- which matches the dashboard measure. It is not the average of the
-- route-day rate column.
CREATE OR REPLACE VIEW rail_ops_marts.v_kpi_exec_daily AS
SELECT
  d.date_key,
  d.day_name,
  d.is_weekend,
  o.punctuality_6min,
  o.avg_arrival_delay_min,
  o.cancellation_rate,
  c.passengers,
  c.avg_load_factor,
  c.revenue_eur
FROM rail_ops_marts.dim_date d
LEFT JOIN rail_ops_marts.v_kpi_ops_daily o ON o.date_key = d.date_key
LEFT JOIN (
  SELECT date_key, SUM(passengers) AS passengers,
         SAFE_DIVIDE(SUM(passengers), SUM(seats_total)) AS avg_load_factor,
         SUM(revenue_eur) AS revenue_eur
  FROM rail_ops_marts.v_kpi_route_daily GROUP BY 1
) c ON c.date_key = d.date_key
WHERE o.date_key IS NOT NULL OR c.date_key IS NOT NULL;
