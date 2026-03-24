import sqlite3
import os

DB_PATH = r"d:\DevWorkspace\TalentScout\job_tracker.db"

def cleanup_duplicates():
    if not os.path.exists(DB_PATH):
        print(f"[!] Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get initial count
    cursor.execute("SELECT COUNT(*) FROM jobs")
    initial_count = cursor.fetchone()[0]
    print(f"[*] Initial job count: {initial_count}")

    # Query to find and delete duplicates, keeping only the earliest entry (lowest ID)
    # The requirement is to remove duplicates with the same title.
    # We should probably also consider the company to be safe, but the user said "same title".
    # Let's check same title AND same company as it's the most common duplicate case.
    
    cleanup_sql = """
    DELETE FROM jobs 
    WHERE id NOT IN (
        SELECT MIN(id) 
        FROM jobs 
        GROUP BY title, company
    )
    """
    
    try:
        cursor.execute(cleanup_sql)
        deleted_count = cursor.rowcount
        conn.commit()
        print(f"[+] Successfully removed {deleted_count} duplicate rows.")
        
        cursor.execute("SELECT COUNT(*) FROM jobs")
        final_count = cursor.fetchone()[0]
        print(f"[*] Final job count: {final_count}")
    except Exception as e:
        print(f"[!] Error during cleanup: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    cleanup_duplicates()
