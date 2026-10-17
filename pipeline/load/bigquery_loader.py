"""Load CSVs into BigQuery raw dataset and run SQL models in order.

Uses BigQuery load jobs (bulk path, free tier), then executes the sql/
directory in lexical order: 00_setup -> 10_raw -> 20_staging -> 30_marts.

train_runs and the latest stop_events snapshot are replaced on each run
(WRITE_TRUNCATE). stop_events_history is appended, because the Timetables
API only returns a near-term window and a truncate was wiping every prior
service date. Models are idempotent (CREATE OR REPLACE plus this merge of
snapshots), so the pipeline can re-run without manual cleanup.

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


def write_disposition_for(table: str) -> str:
    """Latest-file mirrors are replaced. Stop-event history is appended."""
    if table.endswith("stop_events_history"):
        return bigquery.WriteDisposition.WRITE_APPEND
    return bigquery.WriteDisposition.WRITE_TRUNCATE


def load_csv(
    bq: bigquery.Client,
    csv_path: Path,
    table: str,
    write_disposition: str | None = None,
) -> None:
    """Bulk-load a CSV into an existing raw table."""
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        write_disposition=write_disposition or write_disposition_for(table),
        # Schema comes from the pre-created table (sql/10_raw) -- never autodetect,
        # so a malformed CSV fails loudly instead of silently changing types.
        autodetect=False,
    )
    with csv_path.open("rb") as fh:
        job = bq.load_table_from_file(fh, f"{config.GCP['project']}.{table}", job_config=job_config)
    job.result()
    log.info("Loaded %s -> %s (%s rows)", csv_path.name, table, job.output_rows)


def _seed_stop_event_history(bq: bigquery.Client) -> None:
    """Copy the current snapshot into history once.

    Tables that were loaded with WRITE_TRUNCATE already hold the only
    operational dates we have (a few service dates, not a backfill). Copy
    them before the snapshot is replaced. No-op once history has any row.
    The count and the insert are separate statements so the insert does not
    read the table it writes.
    """
    raw = config.BQ_DATASETS["raw"]
    log.info("Seeding %s.stop_events_history from the current snapshot if empty", raw)
    n = list(bq.query(f"SELECT COUNT(*) AS n FROM {raw}.stop_events_history").result())[0].n
    if n:
        return
    bq.query(
        f"INSERT INTO {raw}.stop_events_history SELECT * FROM {raw}.stop_events"
    ).result()


def full_load() -> None:
    """Setup datasets, bulk-load raw CSVs, build staging + marts."""
    bq = client()
    run_sql_stage(bq, "00_setup")
    run_sql_stage(bq, "10_raw")
    _seed_stop_event_history(bq)
    for csv_name, table in RAW_LOADS.items():
        csv_path = config.DATA_DIR / csv_name
        if csv_path.exists():
            load_csv(bq, csv_path, table)
        else:
            log.warning("%s missing -- skipped (run ingestion first)", csv_name)
    history_table = f"{config.BQ_DATASETS['raw']}.stop_events_history"
    stop_csv = config.DATA_DIR / "stop_events.csv"
    if stop_csv.exists():
        load_csv(bq, stop_csv, history_table)
    else:
        log.warning("stop_events.csv missing -- history not extended")
    run_sql_stage(bq, "20_staging")
    run_sql_stage(bq, "30_marts")
    log.info("Warehouse build complete.")
