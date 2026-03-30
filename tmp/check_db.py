import sqlite3
import os

DB_PATH = "job_tracker.db"

def check_latest_jobs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT datetime(date_added), title, company FROM jobs ORDER BY date_added DESC LIMIT 5")
    rows = cursor.fetchall()
    print("Latest Jobs:")
    for row in rows:
        print(f"{row[0]}: {row[1]} at {row[2]}")
    conn.close()

if __name__ == "__main__":
    check_latest_jobs()
