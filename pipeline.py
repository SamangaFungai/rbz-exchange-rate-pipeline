"""
pipeline.py
Orchestrates one end-to-end run: extract -> parse -> load -> log.

Usage:
    python pipeline.py                  # runs for today
    python pipeline.py --date 2026-09-25
"""

import argparse
import logging
from datetime import date, datetime

from extract import fetch_pdf, build_url
from parse_pdf import parse_pdf_bytes
from db import init_db, insert_rates, log_run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("pipeline")


def run_for_date(d: date) -> str:
    """Runs the pipeline for a single date. Returns the resulting status."""
    status, content, url = fetch_pdf(d)

    if status == "not_found":
        msg = f"No rates published for {d} (weekend/holiday) — {url}"
        log.info(msg)
        log_run(d.isoformat(), "skipped", 0, msg)
        return "skipped"

    if status == "error":
        msg = f"Failed to fetch {url}"
        log.error(msg)
        log_run(d.isoformat(), "failed", 0, msg)
        return "failed"

    try:
        date_str, rows = parse_pdf_bytes(content)
    except ValueError as e:
        msg = f"Parse error for {url}: {e}"
        log.error(msg)
        log_run(d.isoformat(), "failed", 0, msg)
        return "failed"

    n = insert_rates(rows, date_str, url)
    msg = f"Loaded {n} rows for {date_str} from {url}"
    log.info(msg)
    log_run(date_str, "success", n, msg)
    return "success"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the RBZ rate pipeline for one date.")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Date to fetch, format YYYY-MM-DD. Defaults to today.",
    )
    args = parser.parse_args()

    target_date = (
        datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    )

    init_db()
    result = run_for_date(target_date)
    log.info(f"Pipeline finished with status: {result}")
