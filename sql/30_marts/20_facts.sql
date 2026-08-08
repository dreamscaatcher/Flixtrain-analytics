-- Fact tables. Grain documented on each table -- non-negotiable.

-- Grain: one row per train x station x event (arrival or departure).
CREATE OR REPLACE TABLE rail_ops_marts.fact_stop_events AS
SELECT
  CONCAT(stop_id, '-', event_type)           AS stop_event_key,
  service_date                               AS date_key,
  station_eva                                AS station_key,
  train_id                                   AS train_key,
  event_type,
  planned_time,
  actual_time,
  delay_minutes,
  delay_minutes < 6                          AS is_punctual_6,    -- DB standard
  delay_minutes < 16                         AS is_punctual_15,
  cancelled,
  platform_changed,
  planned_hour
FROM rail_ops_staging.stg_stop_events;

-- Grain: one row per train run (train x route x service date).
-- Commercial columns are SYNTHETIC (see docs/data_dictionary.md).
-- Delay enrichment joins real stop events where the train number matches.
CREATE OR REPLACE TABLE rail_ops_marts.fact_train_runs AS
SELECT
  CONCAT(CAST(r.service_date AS STRING), '-', r.train_number, '-', r.route_id) AS train_run_key,
  r.service_date                             AS date_key,
  r.route_id                                 AS route_key,
  r.train_number,
  r.departure_hour,
  r.seats_total,
  r.seats_sold,
  r.load_factor,
  r.avg_ticket_price_eur,
  r.revenue_eur,
  r.seat_km,
  r.revenue_per_seat_km,
  d.max_arrival_delay,
  r.is_synthetic
FROM rail_ops_staging.stg_train_runs r
LEFT JOIN (
  SELECT train_number, service_date,
         MAX(IF(event_type = 'ARRIVAL', delay_minutes, NULL)) AS max_arrival_delay
  FROM rail_ops_staging.stg_stop_events
  GROUP BY 1, 2
) d
  ON d.train_number = r.train_number
 AND d.service_date = r.service_date;
