"""Every SQL model must parse as valid BigQuery (GoogleSQL) syntax.

Cheap CI guard: catches dialect leftovers (e.g. Snowflake IFF/DATEDIFF) and
typos without needing warehouse credentials.
"""
import sqlglot
import pytest

from pipeline import config

SQL_FILES = sorted((config.ROOT / "sql").rglob("*.sql"))


def test_sql_files_exist():
    assert len(SQL_FILES) == 6


@pytest.mark.parametrize("path", SQL_FILES, ids=lambda p: p.name)
def test_parses_as_bigquery(path):
    for stmt in path.read_text(encoding="utf-8").split(";"):
        if stmt.strip():
            sqlglot.parse_one(stmt, dialect="bigquery")  # raises on invalid syntax
