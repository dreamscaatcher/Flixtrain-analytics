-- STAGING: typed, deduplicated, derived columns computed ONCE here
-- (single source of truth -- no KPI logic ever lives in a dashboard).

-- Stop events: dedupe on (stop_id, event_type) keeping the latest load,
-- compute delay minutes from planned vs changed time.
CREATE OR REPLACE VIEW STAGING.STG_STOP_EVENTS AS
WITH deduped AS (
  SELECT *,
         ROW_NUMBER() OVER (
           PARTITION BY STOP_ID, EVENT_TYPE
           ORDER BY LOADED_AT DESC, CHANGED_TIME DESC NULLS LAST
         ) AS RN
  FROM RAW.STOP_EVENTS
)
SELECT
  STOP_ID,
  STATION_EVA,
  STATION_NAME,
  TRAIN_CATEGORY,
  TRAIN_NUMBER,
  TRAIN_CATEGORY || ' ' || TRAIN_NUMBER                       AS TRAIN_ID,
  LINE,
  EVENT_TYPE,
  PLANNED_TIME,
  CHANGED_TIME,
  COALESCE(CHANGED_TIME, PLANNED_TIME)                        AS ACTUAL_TIME,
  DATEDIFF('minute', PLANNED_TIME,
           COALESCE(CHANGED_TIME, PLANNED_TIME))              AS DELAY_MINUTES,
  CANCELLED,
  PLANNED_PLATFORM,
  CHANGED_PLATFORM,
  (CHANGED_PLATFORM IS NOT NULL
   AND CHANGED_PLATFORM <> ''
   AND CHANGED_PLATFORM <> PLANNED_PLATFORM)                  AS PLATFORM_CHANGED,
  PLANNED_TIME::DATE                                          AS SERVICE_DATE,
  HOUR(PLANNED_TIME)                                          AS PLANNED_HOUR,
  LOADED_AT
FROM deduped
WHERE RN = 1
  AND PLANNED_TIME IS NOT NULL;

-- Train runs: basic sanity filters; derived per-run economics.
CREATE OR REPLACE VIEW STAGING.STG_TRAIN_RUNS AS
SELECT
  SERVICE_DATE,
  TRAIN_NUMBER,
  ROUTE_ID,
  ORIGIN,
  DESTINATION,
  DEPARTURE_HOUR,
  SEATS_TOTAL,
  SEATS_SOLD,
  AVG_TICKET_PRICE_EUR,
  REVENUE_EUR,
  DISTANCE_KM,
  SEATS_SOLD / NULLIF(SEATS_TOTAL, 0)                         AS LOAD_FACTOR,
  SEATS_TOTAL * DISTANCE_KM                                   AS SEAT_KM,
  REVENUE_EUR / NULLIF(SEATS_TOTAL * DISTANCE_KM, 0)          AS REVENUE_PER_SEAT_KM,
  IS_SYNTHETIC
FROM RAW.TRAIN_RUNS
WHERE SEATS_SOLD BETWEEN 0 AND SEATS_TOTAL   -- data quality gate
  AND REVENUE_EUR >= 0;
