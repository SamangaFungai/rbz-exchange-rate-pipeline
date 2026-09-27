"""
backfill.py
Runs the pipeline across a date range to populate historical data.

Since the RBZ URL pattern is predictable, we simply try every weekday
in the range — a 404 (not_found) means no rate was published that day
(public holiday), which the pipeline already treats as "skipped"
rather than an error.

Usage:
    python backfill.py --start 2026-01-01 --end 2026-09-25
"""

import argparse
import time
from datetime import date, datetime, timedelta

from db import init_db
from pipeline import run_for_date

# Be polite to RBZ's server — small delay between requests.
REQUEST_DELAY_SECONDS = 0.5


def daterange_weekdays(start: date, end: date):
    d = start
    while d <= end:
        if d.weekday() < 5:  # Monday=0 ... Friday=4
            yield d
        d += timedelta(days=1)


def run_backfill(start: date, end: date):
    init_db()
    counts = {"success": 0, "skipped": 0, "failed": 0}

    for d in daterange_weekdays(start, end):
        result = run_for_date(d)
        counts[result] = counts.get(result, 0) + 1
        time.sleep(REQUEST_DELAY_SECONDS)

    print("\nBackfill complete.")
    print(f"  Success: {counts['success']}")
    print(f"  Skipped (no publication): {counts['skipped']}")
    print(f"  Failed: {counts['failed']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill RBZ exchange rate history.")
    parser.add_argument("--start", required=True, help="Start date, YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date, YYYY-MM-DD")
    args = parser.parse_args()

    start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end, "%Y-%m-%d").date()

    run_backfill(start_date, end_date)
