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
--
-- NOTE: an earlier version of this table attempted to enrich each synthetic
-- run with real delay data via a LEFT JOIN on (train_number, service_date)
-- against real stg_stop_events. That join never matched: synthetic train
-- numbers are always 1200-1209 (reset daily, see synthetic.py), while real
-- DB train numbers use each operator's own numbering (e.g. ICE 857, RE
-- 11441) -- entirely different ID spaces with no legitimate way to link a
-- synthetic booking to a specific real train run. Verified 0 of 3,600 rows
-- ever matched. Removed rather than shipped as a silently-always-NULL
-- column. Documented as a known limitation in docs/data_dictionary.md.
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
  r.is_synthetic
FROM rail_ops_staging.stg_train_runs r;
