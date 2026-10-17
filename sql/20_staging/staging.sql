-- STAGING: typed, deduplicated, derived columns computed ONCE here
-- (single source of truth -- no KPI logic ever lives in a dashboard).

-- Stop events: union the accumulating history with the latest CSV mirror,
-- then dedupe on (stop_id, event_type).
--
-- Prefer a row that actually observed a delay, cancellation, or platform
-- change over a later plan-only refresh of the same stop. /fchg drops trains
-- after they depart, so a later pull often has a null changed_time and would
-- otherwise erase a real delay (and count the train as on time). When both
-- rows observed a change, the later load wins so a delay revision is kept.
CREATE OR REPLACE VIEW rail_ops_staging.stg_stop_events AS
WITH sourced AS (
  SELECT * FROM rail_ops_raw.stop_events_history
  UNION ALL
  SELECT * FROM rail_ops_raw.stop_events
),
deduped AS (
  SELECT *,
         ROW_NUMBER() OVER (
           PARTITION BY stop_id, event_type
           ORDER BY
             IF(
               changed_time IS NOT NULL
               OR LOWER(cancelled) = 'true'
               OR (
                 changed_platform IS NOT NULL
                 AND changed_platform != ''
                 AND changed_platform != planned_platform
               ),
               1, 0
             ) DESC,
             loaded_at DESC,
             changed_time DESC
         ) AS rn
  FROM sourced
)
SELECT
  stop_id,
  station_eva,
  station_name,
  train_category,
  train_number,
  CONCAT(train_category, ' ', train_number)                   AS train_id,
  line,
  event_type,
  planned_time,
  changed_time,
  COALESCE(changed_time, planned_time)                        AS actual_time,
  DATETIME_DIFF(COALESCE(changed_time, planned_time),
                planned_time, MINUTE)                         AS delay_minutes,
  LOWER(cancelled) = 'true'                                   AS cancelled,
  planned_platform,
  changed_platform,
  (changed_platform IS NOT NULL
   AND changed_platform != ''
   AND changed_platform != planned_platform)                  AS platform_changed,
  DATE(planned_time)                                          AS service_date,
  EXTRACT(HOUR FROM planned_time)                             AS planned_hour,
  loaded_at
FROM deduped
WHERE rn = 1
  AND planned_time IS NOT NULL;

-- Train runs: basic sanity filters and derived per-run economics.
-- (Never put a semicolon inside a comment -- the loader splits files on it.)
CREATE OR REPLACE VIEW rail_ops_staging.stg_train_runs AS
SELECT
  service_date,
  train_number,
  route_id,
  origin,
  destination,
  departure_hour,
  seats_total,
  seats_sold,
  avg_ticket_price_eur,
  revenue_eur,
  distance_km,
  SAFE_DIVIDE(seats_sold, seats_total)                        AS load_factor,
  seats_total * distance_km                                   AS seat_km,
  SAFE_DIVIDE(revenue_eur, seats_total * distance_km)         AS revenue_per_seat_km,
  LOWER(is_synthetic) = 'true'                                AS is_synthetic
FROM rail_ops_raw.train_runs
WHERE seats_sold BETWEEN 0 AND seats_total   -- data quality gate
  AND revenue_eur >= 0;
