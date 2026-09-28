import sqlite3
import json
from pathlib import Path

conn = sqlite3.connect("rbz_rates.db")
cur = conn.cursor()

latest_date = cur.execute("SELECT MAX(date) FROM exchange_rates").fetchone()[0]

latest = [
    {"currency": c, "idx_mid": i, "zwg_mid": z}
    for c, i, z in cur.execute(
        "SELECT currency, idx_mid, zwg_mid FROM exchange_rates "
        "WHERE date = ? ORDER BY currency",
        (latest_date,),
    )
]

history = {}
for d, currency, zwg_mid in cur.execute(
    "SELECT date, currency, zwg_mid FROM exchange_rates ORDER BY date"
):
    history.setdefault(currency, []).append({"date": d, "zwg_mid": zwg_mid})

Path("docs").mkdir(exist_ok=True)
Path("docs/data.json").write_text(
    json.dumps({"latest_date": latest_date, "latest": latest, "history": history})
)
conn.close()
print(f"Exported docs/data.json — {len(latest)} currencies, latest date {latest_date}")
