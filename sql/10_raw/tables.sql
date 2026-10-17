-- RAW layer: schema mirrors the pipeline CSVs exactly. No transformation here.
-- Booleans land as STRING and are cast in staging: raw stays a faithful copy
-- of the source file, and a malformed value fails visibly in one place.
CREATE TABLE IF NOT EXISTS rail_ops_raw.stop_events (
  stop_id            STRING,
  station_eva        INT64,
  station_name       STRING,
  train_category     STRING,
  train_number       STRING,
  line               STRING,
  event_type         STRING,      -- ARRIVAL | DEPARTURE
  planned_time       DATETIME,
  changed_time       DATETIME,
  planned_platform   STRING,
  changed_platform   STRING,
  cancelled          STRING,      -- 'True'/'False' from pipeline CSV
  loaded_at          DATETIME
);

-- Every pipeline run appends its near-term snapshot here. stop_events above
-- stays a mirror of the latest CSV. Staging reads both (see staging.sql).
-- Same columns, same order, so INSERT ... SELECT * stays valid.
CREATE TABLE IF NOT EXISTS rail_ops_raw.stop_events_history (
  stop_id            STRING,
  station_eva        INT64,
  station_name       STRING,
  train_category     STRING,
  train_number       STRING,
  line               STRING,
  event_type         STRING,
  planned_time       DATETIME,
  changed_time       DATETIME,
  planned_platform   STRING,
  changed_platform   STRING,
  cancelled          STRING,
  loaded_at          DATETIME
);

CREATE TABLE IF NOT EXISTS rail_ops_raw.train_runs (
  service_date          DATE,
  train_number          STRING,
  route_id              STRING,
  origin                STRING,
  destination           STRING,
  departure_hour        INT64,
  seats_total           INT64,
  seats_sold            INT64,
  avg_ticket_price_eur  NUMERIC,
  revenue_eur           NUMERIC,
  distance_km           INT64,
  is_synthetic          STRING       -- always 'True': commercial layer is generated
);
