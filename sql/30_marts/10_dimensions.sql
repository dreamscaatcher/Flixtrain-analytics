-- MARTS: star schema. Dimensions first (facts reference them).

-- Calendar dimension: 2 years, generated in-warehouse (no external seed file).
CREATE OR REPLACE TABLE MARTS.DIM_DATE AS
SELECT
  D                                          AS DATE_KEY,
  YEAR(D)                                    AS YEAR,
  QUARTER(D)                                 AS QUARTER,
  MONTH(D)                                   AS MONTH,
  MONTHNAME(D)                               AS MONTH_NAME,
  WEEKISO(D)                                 AS ISO_WEEK,
  DAYOFWEEKISO(D)                            AS ISO_DAY_OF_WEEK,   -- 1=Mon .. 7=Sun
  DAYNAME(D)                                 AS DAY_NAME,
  DAYOFWEEKISO(D) >= 6                       AS IS_WEEKEND
FROM (
  SELECT DATEADD('day', SEQ4(), '2026-01-01'::DATE) AS D
  FROM TABLE(GENERATOR(ROWCOUNT => 730))
);

CREATE OR REPLACE TABLE MARTS.DIM_STATION AS
SELECT DISTINCT
  STATION_EVA                                AS STATION_KEY,
  STATION_NAME
FROM STAGING.STG_STOP_EVENTS;

CREATE OR REPLACE TABLE MARTS.DIM_ROUTE AS
SELECT DISTINCT
  ROUTE_ID                                   AS ROUTE_KEY,
  ORIGIN,
  DESTINATION,
  DISTANCE_KM
FROM STAGING.STG_TRAIN_RUNS;

CREATE OR REPLACE TABLE MARTS.DIM_TRAIN AS
SELECT DISTINCT
  TRAIN_ID                                   AS TRAIN_KEY,
  TRAIN_CATEGORY,
  TRAIN_NUMBER,
  TRAIN_CATEGORY = 'FLX'                     AS IS_FLIX_TRAIN
FROM STAGING.STG_STOP_EVENTS;
