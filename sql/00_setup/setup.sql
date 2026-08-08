-- One-time environment setup. Idempotent: safe to re-run.
-- BigQuery layers as datasets (BI reads ONLY from rail_ops_marts).
CREATE SCHEMA IF NOT EXISTS rail_ops_raw     OPTIONS (location = 'EU');
CREATE SCHEMA IF NOT EXISTS rail_ops_staging OPTIONS (location = 'EU');
CREATE SCHEMA IF NOT EXISTS rail_ops_marts   OPTIONS (location = 'EU');
