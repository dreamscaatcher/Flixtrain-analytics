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

CREATE OR REPLACE TABLE rail_ops_marts.dim_station AS
SELECT DISTINCT
  station_eva                                AS station_key,
  station_name
FROM rail_ops_staging.stg_stop_events;

CREATE OR REPLACE TABLE rail_ops_marts.dim_route AS
SELECT DISTINCT
  route_id                                   AS route_key,
  origin,
  destination,
  distance_km
FROM rail_ops_staging.stg_train_runs;

CREATE OR REPLACE TABLE rail_ops_marts.dim_train AS
SELECT DISTINCT
  train_id                                   AS train_key,
  train_category,
  train_number,
  train_category = 'FLX'                     AS is_flix_train
FROM rail_ops_staging.stg_stop_events;
