import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "job_tracker.db")

def cleanup_zero_score_jobs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check how many jobs match this criteria
    # Match jobs that are 'new' AND (score is 0 OR matched_skills is '[]' or matched_skills is NULL)
    cursor.execute("""
        SELECT COUNT(*) FROM jobs 
        WHERE status = 'new' 
        AND (score = 0 OR matched_skills = '[]' OR matched_skills IS NULL)
    """)
    count = cursor.fetchone()[0]
    
    if count > 0:
        cursor.execute("""
            DELETE FROM jobs 
            WHERE status = 'new' 
            AND (score = 0 OR matched_skills = '[]' OR matched_skills IS NULL)
        """)
        conn.commit()
        print(f"[*] Deleted {count} 'new' jobs with 0 score or no matching skills from the database.")
    else:
        print("[*] No 'new' jobs with 0 score found to delete.")
        
    conn.close()

if __name__ == "__main__":
    cleanup_zero_score_jobs()
