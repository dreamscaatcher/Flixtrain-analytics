"""End-to-end pipeline: ingest -> load -> transform.

Usage:
    python -m pipeline.run_pipeline              # full run (needs GCP credentials)
    python -m pipeline.run_pipeline --local-only # ingestion + generation only
    python -m pipeline.run_pipeline --hours 4    # near-term /plan window
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
                        help="Skip BigQuery load (produce CSVs only)")
    parser.add_argument("--days", type=int, default=90,
                        help="Days of synthetic commercial history to generate")
    parser.add_argument(
        "--hours", type=int, default=4,
        help="Hours of /plan to request from now, in Europe/Berlin. "
             "Keep this short (default 4): a long window stores trains whose "
             "delays are not known yet as on time. Punctuality history comes "
             "from retaining each run, not from one wide pull.",
    )
    args = parser.parse_args(argv)

    db_timetables.ingest(hours=args.hours)
    synthetic.generate(days=args.days)

    if args.local_only:
        log.info("Local-only run complete (CSVs in data/).")
        return 0

    from pipeline.load import bigquery_loader  # import here: optional dep at runtime
    bigquery_loader.full_load()
    return 0


if __name__ == "__main__":
    sys.exit(main())
