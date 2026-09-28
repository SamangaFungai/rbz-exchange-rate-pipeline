import sqlite3

conn = sqlite3.connect("rbz_rates.db")
cur = conn.cursor()

# Use the latest log entry per date, not every historical one
rows = cur.execute("""
    SELECT date_requested, status, rows_written
    FROM pipeline_log
    WHERE id IN (
        SELECT MAX(id) FROM pipeline_log GROUP BY date_requested
    )
    ORDER BY date_requested
""").fetchall()

print("Date       | status  | logged | actual")
for d, status, n in rows:
    actual = cur.execute(
        "SELECT COUNT(*) FROM exchange_rates WHERE date = ?", (d,)
    ).fetchone()[0]
    flag = "" if actual == n else "   <-- MISMATCH"
    print(f"{d} | {status:7} | {n:6} | {actual}{flag}")

conn.close()