"""
db.py
Handles all SQLite storage for the RBZ exchange rate pipeline.

Two tables:
  - exchange_rates: one row per (date, currency), holding both the
    "currency indices" cross-rate (vs USD) and the ZWG interbank rate.
  - pipeline_log: one row per pipeline run, for observability.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "rbz_rates.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS exchange_rates (
    date            TEXT NOT NULL,      -- ISO format YYYY-MM-DD
    currency        TEXT NOT NULL,      -- e.g. USD, ZAR, GBP
    idx_bid         REAL,               -- currency index bid (vs USD)
    idx_ask         REAL,
    idx_mid         REAL,
    zwg_bid         REAL,               -- interbank rate in ZWG
    zwg_ask         REAL,
    zwg_mid         REAL,
    source_url      TEXT,
    fetched_at      TEXT,
    UNIQUE(date, currency)
);

CREATE TABLE IF NOT EXISTS pipeline_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at          TEXT NOT NULL,
    date_requested  TEXT NOT NULL,
    status          TEXT NOT NULL,      -- success | skipped | failed
    rows_written    INTEGER DEFAULT 0,
    message         TEXT
);
"""


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    conn = get_connection()
    with conn:
        conn.executescript(SCHEMA)
    conn.close()


def insert_rates(rows, date_str, source_url):
    """
    rows: list of dicts with keys:
        currency, idx_bid, idx_ask, idx_mid, zwg_bid, zwg_ask, zwg_mid
    Uses INSERT OR REPLACE so re-running a day overwrites cleanly
    instead of erroring or duplicating.
    """
    conn = get_connection()
    fetched_at = datetime.utcnow().isoformat()
    with conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO exchange_rates
                (date, currency, idx_bid, idx_ask, idx_mid,
                 zwg_bid, zwg_ask, zwg_mid, source_url, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    date_str,
                    r["currency"],
                    r["idx_bid"],
                    r["idx_ask"],
                    r["idx_mid"],
                    r["zwg_bid"],
                    r["zwg_ask"],
                    r["zwg_mid"],
                    source_url,
                    fetched_at,
                )
                for r in rows
            ],
        )
    conn.close()
    return len(rows)


def log_run(date_str, status, rows_written=0, message=""):
    conn = get_connection()
    with conn:
        conn.execute(
            """
            INSERT INTO pipeline_log (run_at, date_requested, status, rows_written, message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (datetime.utcnow().isoformat(), date_str, status, rows_written, message),
        )
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Initialized database at {DB_PATH}")
