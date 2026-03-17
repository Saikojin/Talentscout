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
                    date_added TEXT
                )
            """)
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

def add_job(title, company, url, site_source):
    """Add a new job to the database if it doesn't exist."""
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            date_added = datetime.datetime.now().isoformat()
            cursor.execute("""
                INSERT OR IGNORE INTO jobs (title, company, url, site_source, status, date_added)
                VALUES (?, ?, ?, ?, 'new', ?)
            """, (title, company, url, site_source, date_added))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error adding job: {e}")
        finally:
            conn.close()

# Initialize DB on import
init_db()
