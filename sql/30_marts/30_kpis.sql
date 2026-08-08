-- KPI views: the ONLY layer BI tools read. Definitions live here, once.
-- Full business definitions: docs/kpi_definitions.md

-- Daily operational KPIs (real data).
CREATE OR REPLACE VIEW rail_ops_marts.v_kpi_ops_daily AS
SELECT
  date_key,
  COUNT(*)                                                    AS stop_events,
  COUNT(DISTINCT train_key)                                   AS trains,
  AVG(IF(event_type = 'ARRIVAL', delay_minutes, NULL))        AS avg_arrival_delay_min,
  AVG(IF(event_type = 'ARRIVAL',
         IF(is_punctual_6, 1, 0), NULL))                      AS punctuality_6min,
  AVG(IF(event_type = 'ARRIVAL',
         IF(is_punctual_15, 1, 0), NULL))                     AS punctuality_15min,
  AVG(IF(cancelled, 1, 0))                                    AS cancellation_rate,
  AVG(IF(platform_changed, 1, 0))                             AS platform_change_rate
FROM rail_ops_marts.fact_stop_events
GROUP BY date_key;

-- Station-level delay picture (real data).
CREATE OR REPLACE VIEW rail_ops_marts.v_kpi_station AS
SELECT
  f.station_key,
  s.station_name,
  COUNT(*)                                                    AS stop_events,
  AVG(IF(f.event_type = 'ARRIVAL', f.delay_minutes, NULL))    AS avg_arrival_delay_min,
  AVG(IF(f.event_type = 'ARRIVAL',
         IF(f.is_punctual_6, 1, 0), NULL))                    AS punctuality_6min,
  AVG(IF(f.cancelled, 1, 0))                                  AS cancellation_rate
FROM rail_ops_marts.fact_stop_events f
JOIN rail_ops_marts.dim_station s ON s.station_key = f.station_key
GROUP BY 1, 2;

-- Route-level commercial KPIs (synthetic overlay), daily.
CREATE OR REPLACE VIEW rail_ops_marts.v_kpi_route_daily AS
SELECT
  f.date_key,
  f.route_key,
  r.origin,
  r.destination,
  COUNT(*)                                                    AS train_runs,
  SUM(f.seats_sold)                                           AS passengers,
  AVG(f.load_factor)                                          AS avg_load_factor,
  SUM(f.revenue_eur)                                          AS revenue_eur,
  SAFE_DIVIDE(SUM(f.revenue_eur), SUM(f.seat_km))             AS revenue_per_seat_km,
  AVG(f.max_arrival_delay)                                    AS avg_max_arrival_delay
FROM rail_ops_marts.fact_train_runs f
JOIN rail_ops_marts.dim_route r ON r.route_key = f.route_key
GROUP BY 1, 2, 3, 4;

-- Executive daily rollup: ops + commercial in one row per day.
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
         AVG(avg_load_factor) AS avg_load_factor,
         SUM(revenue_eur) AS revenue_eur
  FROM rail_ops_marts.v_kpi_route_daily GROUP BY 1
) c ON c.date_key = d.date_key
WHERE o.date_key IS NOT NULL OR c.date_key IS NOT NULL;
