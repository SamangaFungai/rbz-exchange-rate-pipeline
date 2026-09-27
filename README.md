# RBZ Exchange Rate ETL Pipeline

Daily ETL pipeline that pulls Zimbabwe's official interbank exchange rates
(published by the Reserve Bank of Zimbabwe) from their site, parses the
published PDF, and loads structured, queryable history into SQLite.

## Why this project

RBZ publishes daily rates only as small PDFs, one per business day, with
no public API. This pipeline turns that into a clean, queryable dataset —
useful for tracking ZWG depreciation over time, building a dashboard on
top of, or feeding into other analysis.

## Architecture

```
extract.py   -> builds the day's PDF URL and downloads it
parse_pdf.py -> extracts the rate table from the PDF (pdfplumber)
db.py        -> SQLite schema + insert/log helpers
pipeline.py  -> orchestrates one day's extract -> parse -> load -> log
backfill.py  -> loops pipeline.py across a date range for historical data
```

**Source:** `https://www.rbz.co.zw/documents/Exchange_Rates/{YEAR}/{Month}/RATES_{DD}_{MONTH}_{YEAR}.pdf`
Confirmed pattern, e.g. `RATES_25_SEPTEMBER_2026.pdf`. RBZ only publishes
on business days — a 404 for a weekend/holiday is expected and handled
as "skipped", not an error.

**Data captured per currency, per day:**
- `idx_bid / idx_ask / idx_mid` — the currency's cross-rate index vs USD
- `zwg_bid / zwg_ask / zwg_mid` — the actual interbank rate in ZWG (what you usually want)

## Setup

```bash
pip install -r requirements.txt
```

## Usage

Run for today:
```bash
python pipeline.py
```

Run for a specific date:
```bash
python pipeline.py --date 2026-09-25
```

Backfill a range of history:
```bash
python backfill.py --start 2026-01-01 --end 2026-09-25
```

## Scheduling (daily automation)

On Linux/Mac, add to crontab (`crontab -e`) to run every weekday at 17:00,
after RBZ typically publishes:

```
0 17 * * 1-5 cd /path/to/rbz_pipeline && /usr/bin/python3 pipeline.py >> pipeline.log 2>&1
```

## Example queries

```sql
-- USD/ZWG mid rate over time
SELECT date, zwg_mid FROM exchange_rates WHERE currency = 'USD' ORDER BY date;

-- Latest rate for every currency
SELECT * FROM exchange_rates WHERE date = (SELECT MAX(date) FROM exchange_rates);

-- Pipeline run history / failures
SELECT * FROM pipeline_log WHERE status != 'success' ORDER BY run_at DESC;
```

## Possible extensions

- Build a dashboard (Streamlit/Power BI) on top of `rbz_rates.db` — this pairs
  directly with the "business dashboard" project in the same portfolio.
- Add alerting (e.g. email/Slack) if the ZWG mid rate moves more than X% day-over-day.
- Cross-reference against Frankfurter/ECB rates for USD/ZAR/GBP/EUR to compare
  official Zimbabwean rates against international benchmarks.
- Scale scheduling to Airflow/Prefect if this needed to run across many sources.

## Notes for the write-up

Mention in your resume/portfolio README that this pipeline:
- Handles a real-world, undocumented data source (no public API) — including
  determining the URL pattern and PDF structure through inspection.
- Distinguishes "no data published" (expected, e.g. weekends) from genuine
  failures — a nuance that matters in production pipelines.
- Uses `INSERT OR REPLACE` so re-running a date is idempotent (safe to retry).
