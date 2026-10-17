-- MARTS: star schema. Dimensions first (facts reference them).

-- Calendar dimension: 2 years, generated in-warehouse (no external seed file).
CREATE OR REPLACE TABLE rail_ops_marts.dim_date AS
SELECT
  d                                          AS date_key,
  EXTRACT(YEAR FROM d)                       AS year,
  EXTRACT(QUARTER FROM d)                    AS quarter,
  EXTRACT(MONTH FROM d)                      AS month,
  FORMAT_DATE('%B', d)                       AS month_name,
  EXTRACT(ISOWEEK FROM d)                    AS iso_week,
  MOD(EXTRACT(DAYOFWEEK FROM d) + 5, 7) + 1  AS iso_day_of_week,   -- 1=Mon .. 7=Sun
  FORMAT_DATE('%A', d)                       AS day_name,
  MOD(EXTRACT(DAYOFWEEK FROM d) + 5, 7) + 1 >= 6 AS is_weekend
FROM UNNEST(GENERATE_DATE_ARRAY('2026-01-01', '2027-12-31')) AS d;

-- station_name_short drops a parenthetical qualifier so a label fits:
-- Frankfurt (Main) Hbf -> Frankfurt Hbf. The full station_name stays.
CREATE OR REPLACE TABLE rail_ops_marts.dim_station AS
SELECT DISTINCT
  station_eva                                AS station_key,
  station_name,
  REGEXP_REPLACE(station_name, r'\s*\([^)]*\)', '') AS station_name_short
FROM rail_ops_staging.stg_stop_events;

-- route_label is the legend/axis name. It drops the parenthetical and a
-- trailing Hbf / Sued / Bad Bf / Bf:
-- Karlsruhe Hbf -> Freiburg (Breisgau) Hbf becomes Karlsruhe – Freiburg.
-- Full origin and destination stay for the route table and slicers.
CREATE OR REPLACE TABLE rail_ops_marts.dim_route AS
SELECT DISTINCT
  route_id                                   AS route_key,
  origin,
  destination,
  REGEXP_REPLACE(origin, r'\s*\([^)]*\)', '')       AS origin_short,
  REGEXP_REPLACE(destination, r'\s*\([^)]*\)', '')  AS destination_short,
  CONCAT(
    REGEXP_REPLACE(REGEXP_REPLACE(origin, r'\s*\([^)]*\)', ''), r'\s+(Hbf|Sued|Bad Bf|Bf)$', ''),
    ' – ',
    REGEXP_REPLACE(REGEXP_REPLACE(destination, r'\s*\([^)]*\)', ''), r'\s+(Hbf|Sued|Bad Bf|Bf)$', '')
  )                                          AS route_label,
  distance_km
FROM rail_ops_staging.stg_train_runs;

CREATE OR REPLACE TABLE rail_ops_marts.dim_train AS
SELECT DISTINCT
  train_id                                   AS train_key,
  train_category,
  train_number,
  train_category = 'FLX'                     AS is_flix_train
FROM rail_ops_staging.stg_stop_events;
