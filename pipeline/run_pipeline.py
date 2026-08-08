"""End-to-end pipeline: ingest -> load -> transform.

Usage:
    python -m pipeline.run_pipeline              # full run (needs Snowflake creds)
    python -m pipeline.run_pipeline --local-only # ingestion + generation only
"""
from __future__ import annotations

import argparse
import logging
import sys

from pipeline.ingest import db_timetables, synthetic

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("pipeline")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rail ops analytics pipeline")
    parser.add_argument("--local-only", action="store_true",
                        help="Skip Snowflake load (produce CSVs only)")
    parser.add_argument("--days", type=int, default=90,
                        help="Days of synthetic commercial history to generate")
    args = parser.parse_args(argv)

    db_timetables.ingest()
    synthetic.generate(days=args.days)

    if args.local_only:
        log.info("Local-only run complete (CSVs in data/).")
        return 0

    from pipeline.load import snowflake_loader  # import here: optional dep at runtime
    snowflake_loader.full_load()
    return 0


if __name__ == "__main__":
    sys.exit(main())
