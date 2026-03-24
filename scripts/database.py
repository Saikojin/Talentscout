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
                
            # Create sites table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    search_url TEXT,
                    job_card_selector TEXT,
                    title_selector TEXT,
                    company_selector TEXT,
                    job_url_selector TEXT
                )
            """)
            
            # Create search_configs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    site_id INTEGER NOT NULL,
                    search_terms TEXT,
                    locations TEXT,
                    filters TEXT,
                    FOREIGN KEY(site_id) REFERENCES sites(id) ON DELETE CASCADE
                )
            """)
            
            # Create companies table for direct crawling
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    careers_url TEXT UNIQUE NOT NULL,
                    job_card_selector TEXT,
                    title_selector TEXT,
                    company_selector TEXT,
                    job_url_selector TEXT,
                    date_added TEXT
                )
            """)
                
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error initializing database: {e}")
        finally:
            conn.close()

def is_duplicate(url, title=None, company=None):
    """Check if the given URL already exists in the database or if title/company combo exists, and its status is not 'new'."""
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            # First check by URL
            cursor.execute("SELECT status FROM jobs WHERE url = ?", (url,))
            row = cursor.fetchone()
            if row is not None:
                return row[0].lower() != 'new'
            
            # If URL not found, check by title and company if provided
            if title and company:
                cursor.execute("SELECT status FROM jobs WHERE title = ? AND company = ?", (title, company))
                row = cursor.fetchone()
                if row is not None:
                    return row[0].lower() != 'new'
                    
            return False
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

# --- Site Configuration CRUD Methods ---

def add_site(name, search_url, job_card_selector, title_selector, company_selector, job_url_selector):
    conn = create_connection()
    site_id = None
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sites (name, search_url, job_card_selector, title_selector, company_selector, job_url_selector)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, search_url, job_card_selector, title_selector, company_selector, job_url_selector))
            conn.commit()
            site_id = cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding site: {e}")
        finally:
            conn.close()
    return site_id

def update_site(site_id, name, search_url, job_card_selector, title_selector, company_selector, job_url_selector):
    conn = create_connection()
    success = False
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sites 
                SET name=?, search_url=?, job_card_selector=?, title_selector=?, company_selector=?, job_url_selector=?
                WHERE id=?
            """, (name, search_url, job_card_selector, title_selector, company_selector, job_url_selector, site_id))
            conn.commit()
            success = cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating site: {e}")
        finally:
            conn.close()
    return success

def delete_site(site_id):
    conn = create_connection()
    success = False
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sites WHERE id=?", (site_id,))
            conn.commit()
            success = cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error deleting site: {e}")
        finally:
            conn.close()
    return success

def get_all_sites():
    conn = create_connection()
    sites = []
    if conn is not None:
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sites")
            rows = cursor.fetchall()
            for row in rows:
                sites.append(dict(row))
        except sqlite3.Error as e:
            print(f"Error fetching sites: {e}")
        finally:
            conn.close()
    return sites

def add_search_config(site_id, search_terms, locations, filters):
    import json
    conn = create_connection()
    config_id = None
    if conn is not None:
        try:
            cursor = conn.cursor()
            st_json = json.dumps(search_terms) if isinstance(search_terms, list) else search_terms
            loc_json = json.dumps(locations) if isinstance(locations, list) else locations
            fil_json = json.dumps(filters) if isinstance(filters, dict) else filters
            
            cursor.execute("""
                INSERT INTO search_configs (site_id, search_terms, locations, filters)
                VALUES (?, ?, ?, ?)
            """, (site_id, st_json, loc_json, fil_json))
            conn.commit()
            config_id = cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding search config: {e}")
        finally:
            conn.close()
    return config_id

def update_search_config(config_id, site_id, search_terms, locations, filters):
    import json
    conn = create_connection()
    success = False
    if conn is not None:
        try:
            cursor = conn.cursor()
            st_json = json.dumps(search_terms) if isinstance(search_terms, list) else search_terms
            loc_json = json.dumps(locations) if isinstance(locations, list) else locations
            fil_json = json.dumps(filters) if isinstance(filters, dict) else filters
            
            cursor.execute("""
                UPDATE search_configs 
                SET site_id=?, search_terms=?, locations=?, filters=?
                WHERE id=?
            """, (site_id, st_json, loc_json, fil_json, config_id))
            conn.commit()
            success = cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating search config: {e}")
        finally:
            conn.close()
    return success

def delete_search_config(config_id):
    conn = create_connection()
    success = False
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM search_configs WHERE id=?", (config_id,))
            conn.commit()
            success = cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error deleting config: {e}")
        finally:
            conn.close()
    return success

def get_all_search_configs():
    import json
    conn = create_connection()
    configs = []
    if conn is not None:
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            # Join with sites to make it easy to use in auto_scour.py
            cursor.execute("""
                SELECT c.*, s.name as site_name, s.search_url, s.job_card_selector, 
                       s.title_selector, s.company_selector, s.job_url_selector
                FROM search_configs c
                JOIN sites s ON c.site_id = s.id
            """)
            rows = cursor.fetchall()
            for row in rows:
                d = dict(row)
                d['search_terms'] = json.loads(d['search_terms']) if d['search_terms'] else []
                d['locations'] = json.loads(d['locations']) if d['locations'] else []
                d['filters'] = json.loads(d['filters']) if d['filters'] else {}
                configs.append(d)
        except sqlite3.Error as e:
            print(f"Error fetching search configs: {e}")
        finally:
            conn.close()
    return configs

# --- Companies CRUD Methods ---

def add_company(name, careers_url, job_card_selector, title_selector, company_selector, job_url_selector):
    import datetime
    conn = create_connection()
    company_id = None
    if conn is not None:
        try:
            cursor = conn.cursor()
            date_added = datetime.datetime.now().isoformat()
            cursor.execute("""
                INSERT OR IGNORE INTO companies (name, careers_url, job_card_selector, title_selector, company_selector, job_url_selector, date_added)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, careers_url, job_card_selector, title_selector, company_selector, job_url_selector, date_added))
            conn.commit()
            company_id = cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding company: {e}")
        finally:
            conn.close()
    return company_id

def update_company(company_id, name, careers_url, job_card_selector, title_selector, company_selector, job_url_selector):
    conn = create_connection()
    success = False
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE companies 
                SET name=?, careers_url=?, job_card_selector=?, title_selector=?, company_selector=?, job_url_selector=?
                WHERE id=?
            """, (name, careers_url, job_card_selector, title_selector, company_selector, job_url_selector, company_id))
            conn.commit()
            success = cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating company: {e}")
        finally:
            conn.close()
    return success

def delete_company(company_id):
    conn = create_connection()
    success = False
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM companies WHERE id=?", (company_id,))
            conn.commit()
            success = cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error deleting company: {e}")
        finally:
            conn.close()
    return success

def get_all_companies():
    conn = create_connection()
    companies = []
    if conn is not None:
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM companies")
            rows = cursor.fetchall()
            for row in rows:
                companies.append(dict(row))
        except sqlite3.Error as e:
            print(f"Error fetching companies: {e}")
        finally:
            conn.close()
    return companies

def company_exists_by_domain(domain):
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            # simple LIKE comparison to check if domain is in careers_url
            cursor.execute("SELECT id FROM companies WHERE careers_url LIKE ?", ('%' + domain + '%',))
            row = cursor.fetchone()
            return row is not None
        except sqlite3.Error as e:
            print(f"Error checking company domain: {e}")
            return False
        finally:
            conn.close()
    return False
