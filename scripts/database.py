import sqlite3
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "job_tracker.db")

def create_connection():
    """Create a database connection to the SQLite database specified by DB_PATH."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
    return conn

def init_db():
    """Initialize the database schema."""
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    site_source TEXT,
                    status TEXT DEFAULT 'new',
                    date_added TEXT,
                    score INTEGER,
                    missing_skills TEXT,
                    matched_skills TEXT
                )
            """)
            
            # Migration logic for existing DBs
            cursor.execute("PRAGMA table_info(jobs)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'score' not in columns:
                cursor.execute("ALTER TABLE jobs ADD COLUMN score INTEGER")
            if 'missing_skills' not in columns:
                cursor.execute("ALTER TABLE jobs ADD COLUMN missing_skills TEXT")
            if 'matched_skills' not in columns:
                cursor.execute("ALTER TABLE jobs ADD COLUMN matched_skills TEXT")
                
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error initializing database: {e}")
        finally:
            conn.close()

def is_duplicate(url):
    """Check if the given URL already exists in the database."""
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM jobs WHERE url = ?", (url,))
            row = cursor.fetchone()
            return row is not None
        except sqlite3.Error as e:
            print(f"Error checking duplicate: {e}")
            return False
        finally:
            conn.close()
    return False

def add_job(title, company, url, site_source, score=None, missing_skills=None, matched_skills=None):
    """Add a new job to the database if it doesn't exist."""
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            date_added = datetime.datetime.now().isoformat()
            
            import json
            if isinstance(missing_skills, list):
                missing_skills = json.dumps(missing_skills)
            if isinstance(matched_skills, list):
                matched_skills = json.dumps(matched_skills)
                
            cursor.execute("""
                INSERT OR IGNORE INTO jobs (title, company, url, site_source, status, date_added, score, missing_skills, matched_skills)
                VALUES (?, ?, ?, ?, 'new', ?, ?, ?, ?)
            """, (title, company, url, site_source, date_added, score, missing_skills, matched_skills))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error adding job: {e}")
        finally:
            conn.close()

# Initialize DB on import
init_db()

def update_job_status(job_id, status):
    """Update a job's status."""
    val_status = status.lower()
    if val_status not in ['new', 'applied to', 'rejected']:
        print(f"Invalid status: {status}")
        return False
        
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (val_status, job_id))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating job status: {e}")
            return False
        finally:
            conn.close()
    return False

def get_new_jobs():
    """Fetch all 'new' jobs from the database as a list of dictionaries."""
    conn = create_connection()
    jobs = []
    if conn is not None:
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE status = 'new' ORDER BY id DESC")
            rows = cursor.fetchall()
            for row in rows:
                jobs.append(dict(row))
        except sqlite3.Error as e:
            print(f"Error fetching new jobs: {e}")
        finally:
            conn.close()
    return jobs
