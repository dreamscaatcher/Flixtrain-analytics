"""Load CSVs into Snowflake RAW schema and run SQL models in order.

Uses PUT + COPY INTO (Snowflake's bulk-load path) rather than row inserts,
and executes the sql/ directory in lexical order: 00_setup -> 10_raw ->
20_staging -> 30_marts. Every model is idempotent (CREATE OR REPLACE /
TRUNCATE+COPY), so the pipeline can re-run daily without manual cleanup.
"""
from __future__ import annotations

import logging
from pathlib import Path

import snowflake.connector

from pipeline import config

log = logging.getLogger(__name__)

SQL_DIR = config.ROOT / "sql"

RAW_LOADS = {
    # csv file -> raw table
    "stop_events.csv": "RAW.STOP_EVENTS",
    "train_runs.csv": "RAW.TRAIN_RUNS",
}


def connect():
    return snowflake.connector.connect(
        account=config.SNOWFLAKE["account"],
        user=config.SNOWFLAKE["user"],
        password=config.SNOWFLAKE["password"],
        role=config.SNOWFLAKE["role"],
    )


def run_sql_file(cur, path: Path) -> None:
    """Execute a .sql file statement-by-statement (split on ';')."""
    log.info("Running %s", path.relative_to(config.ROOT))
    for stmt in path.read_text(encoding="utf-8").split(";"):
        if stmt.strip():
            cur.execute(stmt)


def run_sql_stage(cur, stage_dir: str) -> None:
    for path in sorted((SQL_DIR / stage_dir).glob("*.sql")):
        run_sql_file(cur, path)


def load_csv(cur, csv_path: Path, table: str) -> None:
    """PUT the file to the table stage, then COPY INTO the table."""
    db = config.SNOWFLAKE["database"]
    cur.execute(f"USE DATABASE {db}")
    cur.execute(f"USE WAREHOUSE {config.SNOWFLAKE['warehouse']}")
    cur.execute(f"TRUNCATE TABLE IF EXISTS {table}")
    cur.execute(f"PUT file://{csv_path.as_posix()} @%{table.split('.')[1]} OVERWRITE = TRUE")
    cur.execute(
        f"COPY INTO {table} FROM @%{table.split('.')[1]} "
        "FILE_FORMAT = (FORMAT_NAME = RAW.CSV_FORMAT) PURGE = TRUE"
    )
    log.info("Loaded %s -> %s", csv_path.name, table)


def full_load() -> None:
    """Setup objects, bulk-load raw CSVs, build staging + marts."""
    conn = connect()
    try:
        cur = conn.cursor()
        run_sql_stage(cur, "00_setup")
        cur.execute(f"USE DATABASE {config.SNOWFLAKE['database']}")
        cur.execute(f"USE WAREHOUSE {config.SNOWFLAKE['warehouse']}")
        run_sql_stage(cur, "10_raw")
        for csv_name, table in RAW_LOADS.items():
            csv_path = config.DATA_DIR / csv_name
            if csv_path.exists():
                load_csv(cur, csv_path, table)
            else:
                log.warning("%s missing -- skipped (run ingestion first)", csv_name)
        run_sql_stage(cur, "20_staging")
        run_sql_stage(cur, "30_marts")
        log.info("Warehouse build complete.")
    finally:
        conn.close()
