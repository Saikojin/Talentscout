import sqlite3
import os

DB_PATH = "job_tracker.db"

def check_db():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("--- SITES ---")
    cursor.execute("SELECT * FROM sites")
    for row in cursor.fetchall():
        print(row)

    print("\n--- SEARCH CONFIGS ---")
    cursor.execute("SELECT * FROM search_configs")
    for row in cursor.fetchall():
        print(row)

    print("\n--- COMPANIES ---")
    cursor.execute("SELECT * FROM companies")
    for row in cursor.fetchall():
        print(row)

    conn.close()

if __name__ == "__main__":
    check_db()
