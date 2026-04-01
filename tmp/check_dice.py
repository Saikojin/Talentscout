import sqlite3
import os

DB_PATH = "job_tracker.db"

def check_dice():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("--- Checking SITES table for Dice ---")
    cursor.execute("SELECT * FROM sites WHERE name LIKE '%Dice%'")
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(row)
    else:
        print("Dice not found in SITES table.")

    print("\n--- Checking SEARCH_CONFIGS table for Dice ---")
    # Join with sites to find dice
    cursor.execute("""
        SELECT c.*, s.name FROM search_configs c 
        JOIN sites s ON c.site_id = s.id 
        WHERE s.name LIKE '%Dice%'
    """)
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(row)
    else:
        print("Dice not found in SEARCH_CONFIGS table.")

    conn.close()

if __name__ == "__main__":
    check_dice()
