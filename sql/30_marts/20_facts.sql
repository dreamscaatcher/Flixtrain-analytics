-- Fact tables. Grain documented on each table -- non-negotiable.

-- Grain: one row per train x station x event (arrival or departure).
CREATE OR REPLACE TABLE MARTS.FACT_STOP_EVENTS AS
SELECT
  STOP_ID || '-' || EVENT_TYPE               AS STOP_EVENT_KEY,
  SERVICE_DATE                               AS DATE_KEY,
  STATION_EVA                                AS STATION_KEY,
  TRAIN_ID                                   AS TRAIN_KEY,
  EVENT_TYPE,
  PLANNED_TIME,
  ACTUAL_TIME,
  DELAY_MINUTES,
  DELAY_MINUTES < 6                          AS IS_PUNCTUAL_6,    -- DB standard
  DELAY_MINUTES < 16                         AS IS_PUNCTUAL_15,
  CANCELLED,
  PLATFORM_CHANGED,
  PLANNED_HOUR
FROM STAGING.STG_STOP_EVENTS;

-- Grain: one row per train run (train x route x service date).
-- Commercial columns are SYNTHETIC (see docs/data_dictionary.md).
-- Delay enrichment joins real stop events where the train number matches.
CREATE OR REPLACE TABLE MARTS.FACT_TRAIN_RUNS AS
SELECT
  r.SERVICE_DATE || '-' || r.TRAIN_NUMBER || '-' || r.ROUTE_ID AS TRAIN_RUN_KEY,
  r.SERVICE_DATE                             AS DATE_KEY,
  r.ROUTE_ID                                 AS ROUTE_KEY,
  r.TRAIN_NUMBER,
  r.DEPARTURE_HOUR,
  r.SEATS_TOTAL,
  r.SEATS_SOLD,
  r.LOAD_FACTOR,
  r.AVG_TICKET_PRICE_EUR,
  r.REVENUE_EUR,
  r.SEAT_KM,
  r.REVENUE_PER_SEAT_KM,
  d.MAX_ARRIVAL_DELAY,
  r.IS_SYNTHETIC
FROM STAGING.STG_TRAIN_RUNS r
LEFT JOIN (
  SELECT TRAIN_NUMBER, SERVICE_DATE,
         MAX(CASE WHEN EVENT_TYPE = 'ARRIVAL' THEN DELAY_MINUTES END) AS MAX_ARRIVAL_DELAY
  FROM STAGING.STG_STOP_EVENTS
  GROUP BY 1, 2
) d
  ON d.TRAIN_NUMBER = r.TRAIN_NUMBER
 AND d.SERVICE_DATE = r.SERVICE_DATE;
