import sqlite3

conn = sqlite3.connect("rbz_rates.db")
rows = conn.execute(
    "SELECT date_requested, message FROM pipeline_log WHERE status='failed' ORDER BY date_requested"
).fetchall()

print(f"Found {len(rows)} failed dates:\n")
for date_requested, message in rows:
    print(f"{date_requested}: {message}")
