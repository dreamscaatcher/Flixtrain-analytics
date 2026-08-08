"""Load CSVs into BigQuery raw dataset and run SQL models in order.

Uses BigQuery load jobs (bulk path, free tier) with WRITE_TRUNCATE, then
executes the sql/ directory in lexical order: 00_setup -> 10_raw ->
20_staging -> 30_marts. Every model is idempotent (CREATE OR REPLACE /
truncating loads), so the pipeline can re-run daily without manual cleanup.

Auth: Application Default Credentials (`gcloud auth application-default login`
locally, or GOOGLE_APPLICATION_CREDENTIALS pointing at a service-account key
in CI). Works inside the free BigQuery sandbox -- no billing account needed.
"""
from __future__ import annotations

import logging
from pathlib import Path

from google.cloud import bigquery

from pipeline import config

log = logging.getLogger(__name__)

SQL_DIR = config.ROOT / "sql"

RAW_LOADS = {
    # csv file -> raw table (dataset-qualified)
    "stop_events.csv": f"{config.BQ_DATASETS['raw']}.stop_events",
    "train_runs.csv": f"{config.BQ_DATASETS['raw']}.train_runs",
}


def client() -> bigquery.Client:
    return bigquery.Client(project=config.GCP["project"], location=config.GCP["location"])


def run_sql_file(bq: bigquery.Client, path: Path) -> None:
    """Execute a .sql file statement-by-statement (split on ';')."""
    log.info("Running %s", path.relative_to(config.ROOT))
    for stmt in path.read_text(encoding="utf-8").split(";"):
        if stmt.strip():
            bq.query(stmt).result()  # .result() waits and surfaces errors


def run_sql_stage(bq: bigquery.Client, stage_dir: str) -> None:
    for path in sorted((SQL_DIR / stage_dir).glob("*.sql")):
        run_sql_file(bq, path)


def load_csv(bq: bigquery.Client, csv_path: Path, table: str) -> None:
    """Bulk-load a CSV into an existing raw table, replacing its contents."""
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        # Schema comes from the pre-created table (sql/10_raw) -- never autodetect,
        # so a malformed CSV fails loudly instead of silently changing types.
        autodetect=False,
    )
    with csv_path.open("rb") as fh:
        job = bq.load_table_from_file(fh, f"{config.GCP['project']}.{table}", job_config=job_config)
    job.result()
    log.info("Loaded %s -> %s (%s rows)", csv_path.name, table, job.output_rows)


def full_load() -> None:
    """Setup datasets, bulk-load raw CSVs, build staging + marts."""
    bq = client()
    run_sql_stage(bq, "00_setup")
    run_sql_stage(bq, "10_raw")
    for csv_name, table in RAW_LOADS.items():
        csv_path = config.DATA_DIR / csv_name
        if csv_path.exists():
            load_csv(bq, csv_path, table)
        else:
            log.warning("%s missing -- skipped (run ingestion first)", csv_name)
    run_sql_stage(bq, "20_staging")
    run_sql_stage(bq, "30_marts")
    log.info("Warehouse build complete.")
