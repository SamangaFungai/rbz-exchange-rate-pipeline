import sqlite3
from datetime import date, timedelta

conn = sqlite3.connect("rbz_rates.db")
cur = conn.cursor()

tables = [r[0] for r in cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]

for t in tables:
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({t})")]
    count = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"\n=== {t} ===")
    print("Columns:", cols)
    print("Rows:", count)

    date_cols = [c for c in cols if "date" in c.lower()]
    for c in date_cols:
        mn, mx, n = cur.execute(
            f"SELECT MIN({c}), MAX({c}), COUNT(DISTINCT {c}) FROM {t}").fetchone()
        print(f"{c}: {mn} -> {mx}, {n} distinct")

    # gap check on the first date column
    if date_cols and count:
        c = date_cols[0]
        have = {r[0][:10] for r in cur.execute(f"SELECT DISTINCT {c} FROM {t} WHERE {c} IS NOT NULL")}
        try:
            start = date.fromisoformat(min(have))
            end = date.fromisoformat(max(have))
            missing = []
            d = start
            while d <= end:
                if d.isoformat() not in have and d.weekday() < 5:
                    missing.append(d.isoformat())
                d += timedelta(days=1)
            print("Missing weekdays:", missing if missing else "none")
        except ValueError:
            pass

    print("Latest 3 rows:")
    for row in cur.execute(f"SELECT * FROM {t} ORDER BY rowid DESC LIMIT 3"):
        print(row)

conn.close()