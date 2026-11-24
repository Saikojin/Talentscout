import sqlite3
import os
import datetime
import re
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "job_tracker.db")

_VOLATILE_QUERY_PARAMS = frozenset({
    "refid", "trackingid", "position", "pagenum", "ebp", "trk", "trkinfo",
    "currentjobid", "origin", "originalreferer", "midtoken", "midsig",
    "lipi", "lici", "f_tpr", "gclid", "fbclid", "gh_src", "lever-source",
    "lever-origin", "ashby_jid_source", "source", "src", "ref", "referrer",
})
_VOLATILE_QUERY_PREFIXES = ("utm_", "rx_")
_PLACEHOLDER_STRINGS = frozenset({"", "unknown", "unknown title", "unknown company", "n/a", "none"})


def canonicalize_job_url(url):
    """
    Normalize a job URL by stripping volatile tracking/session query parameters
    (e.g., LinkedIn refId/trackingId/position, utm_*, rx_*) and URL fragments while
    preserving meaningful job-identifying query parameters (e.g., jk, gh_jid, jobId).
    """
    if not url or not isinstance(url, str):
        return ""
    raw = url.strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
    except Exception:
        return raw

    if not parsed.scheme or not parsed.netloc:
        return raw

    scheme = "https" if parsed.scheme.lower() in ("http", "https") else parsed.scheme.lower()
    netloc = parsed.netloc.lower().strip()
    path = parsed.path or ""
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    # LinkedIn job view URLs uniquely identify the posting in the path; all query params are tracking noise.
    if netloc.endswith("linkedin.com") and "/jobs/view/" in path.lower():
        query = ""
    else:
        kept = []
        for k, v in parse_qsl(parsed.query, keep_blank_values=False):
            kl = k.lower()
            if kl in _VOLATILE_QUERY_PARAMS or any(kl.startswith(p) for p in _VOLATILE_QUERY_PREFIXES):
                continue
            kept.append((k, v))
        kept.sort()
        query = urlencode(kept, doseq=True)

    return urlunparse((scheme, netloc, path, "", query, ""))


def _normalize_title_company(title, company):
    t = re.sub(r"\s+", " ", (title or "").strip()).lower()
    c = re.sub(r"\s+", " ", (company or "").strip()).lower()
    if t in _PLACEHOLDER_STRINGS or c in _PLACEHOLDER_STRINGS:
        return None
    return (t, c)


def _job_exists_on_cursor(cursor, url, title=None, company=None):
    """Check whether a job already exists in `jobs` (any status) by canonical URL or (title, company)."""
    raw_url = (url or "").strip()
    canon_url = canonicalize_job_url(raw_url)

    if raw_url:
        cursor.execute("SELECT 1 FROM jobs WHERE url = ? LIMIT 1", (raw_url,))
        if cursor.fetchone() is not None:
            return True

    if canon_url and canon_url != raw_url:
        cursor.execute("SELECT 1 FROM jobs WHERE url = ? LIMIT 1", (canon_url,))
        if cursor.fetchone() is not None:
            return True

    # Check legacy rows stored with tracking query params on the same host+path
    if canon_url:
        parsed = urlparse(canon_url)
        if parsed.netloc and parsed.path and parsed.path != "/":
            host_path = f"{parsed.netloc}{parsed.path}"
            cursor.execute("SELECT url FROM jobs WHERE LOWER(url) LIKE ?", (f"%{host_path.lower()}%",))
            for (existing_url,) in cursor.fetchall():
                if canonicalize_job_url(existing_url) == canon_url:
                    return True

    norm_tc = _normalize_title_company(title, company)
    if norm_tc is not None:
        t_norm, c_norm = norm_tc
        cursor.execute(
            "SELECT 1 FROM jobs WHERE LOWER(TRIM(title)) = ? AND LOWER(TRIM(company)) = ? LIMIT 1",
            (t_norm, c_norm),
        )
        if cursor.fetchone() is not None:
            return True

    return False

def create_connection():
    """Create a database connection to the SQLite database specified by DB_PATH."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
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
            if 'score_profile_id' not in columns:
                cursor.execute("ALTER TABLE jobs ADD COLUMN score_profile_id INTEGER")
            if 'location' not in columns:
                cursor.execute("ALTER TABLE jobs ADD COLUMN location TEXT")
            if 'country' not in columns:
                cursor.execute("ALTER TABLE jobs ADD COLUMN country TEXT")
            if 'description' not in columns:
                cursor.execute("ALTER TABLE jobs ADD COLUMN description TEXT")
                
            # Create profiles table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    config TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # Create app_settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # Create sites table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    search_url TEXT,
                    job_card_selector TEXT,
                    title_selector TEXT,
                    company_selector TEXT,
                    job_url_selector TEXT,
                    location_selector TEXT
                )
            """)

            cursor.execute("PRAGMA table_info(sites)")
            site_cols = [col[1] for col in cursor.fetchall()]
            if 'location_selector' not in site_cols:
                cursor.execute("ALTER TABLE sites ADD COLUMN location_selector TEXT")
            if 'search_input_selector' not in site_cols:
                cursor.execute("ALTER TABLE sites ADD COLUMN search_input_selector TEXT")
            if 'expand_button_selector' not in site_cols:
                cursor.execute("ALTER TABLE sites ADD COLUMN expand_button_selector TEXT")
            if 'is_career_directory' not in site_cols:
                cursor.execute("ALTER TABLE sites ADD COLUMN is_career_directory INTEGER DEFAULT 0")
            
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
            
            # Create companies table for direct crawling/ATS harvesting
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    careers_url TEXT UNIQUE NOT NULL,
                    job_card_selector TEXT,
                    title_selector TEXT,
                    company_selector TEXT,
                    job_url_selector TEXT,
                    date_added TEXT,
                    website TEXT,
                    ats_type TEXT,
                    ats_url TEXT,
                    tech_stack TEXT,
                    industry_category TEXT,
                    countries TEXT
                )
            """)
            
            # Migration logic for existing DBs (companies table)
            cursor.execute("PRAGMA table_info(companies)")
            comp_columns = [col[1] for col in cursor.fetchall()]
            for new_col in ['website', 'ats_type', 'ats_url', 'tech_stack', 'industry_category', 'countries', 'location_selector']:
                if new_col not in comp_columns:
                    cursor.execute(f"ALTER TABLE companies ADD COLUMN {new_col} TEXT")

            # Create profile_deliveries table for idempotent per-profile email delta tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS profile_deliveries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER NOT NULL,
                    job_id INTEGER NOT NULL,
                    run_id TEXT NOT NULL,
                    delivered_at TEXT NOT NULL,
                    UNIQUE(profile_id, job_id)
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_profile_deliveries_lookup
                ON profile_deliveries(profile_id, job_id)
            """)

            # Enable WAL mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL")
                
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error initializing database: {e}")
        finally:
            conn.close()

def job_exists(url, title=None, company=None):
    """Return True if a job already exists in `jobs` (any status) by canonical URL or (title, company)."""
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            return _job_exists_on_cursor(cursor, url, title=title, company=company)
        except sqlite3.Error as e:
            print(f"Error checking existing job: {e}")
            return False
        finally:
            conn.close()
    return False


def is_duplicate(url, title=None, company=None):
    """Check if the given job already exists in the database (canonical URL or title+company, any status)."""
    return job_exists(url, title=title, company=company)


def add_job(title, company, url, site_source, score=None, missing_skills=None, matched_skills=None, score_profile_id=None, location=None, country=None, description=None):
    """Add a new job to the database if it doesn't already exist (canonical URL or title+company). Returns inserted job id or None."""
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            clean_url = canonicalize_job_url(url) or (url or "").strip()
            if _job_exists_on_cursor(cursor, clean_url, title=title, company=company):
                return None

            date_added = datetime.datetime.now().isoformat()
            
            import json
            if isinstance(missing_skills, list):
                missing_skills = json.dumps(missing_skills)
            if isinstance(matched_skills, list):
                matched_skills = json.dumps(matched_skills)
                
            cursor.execute("""
                INSERT OR IGNORE INTO jobs (title, company, url, site_source, status, date_added, score, missing_skills, matched_skills, score_profile_id, location, country, description)
                VALUES (?, ?, ?, ?, 'new', ?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, company, clean_url, site_source, date_added, score, missing_skills, matched_skills, score_profile_id, location, country, description))
            conn.commit()
            return cursor.lastrowid if cursor.rowcount > 0 else None
        except sqlite3.Error as e:
            print(f"Error adding job: {e}")
        finally:
            conn.close()
    return None

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

def update_job_description(job_id, description):
    """Store or update the full job description text for a job."""
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE jobs SET description = ? WHERE id = ?", (description or "", job_id))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Error updating job description: {e}")
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

def add_site(name, search_url, job_card_selector, title_selector, company_selector, job_url_selector, location_selector=None):
    conn = create_connection()
    site_id = None
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sites (name, search_url, job_card_selector, title_selector, company_selector, job_url_selector, location_selector)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, search_url, job_card_selector, title_selector, company_selector, job_url_selector, location_selector))
            conn.commit()
            site_id = cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding site: {e}")
        finally:
            conn.close()
    return site_id

def update_site(site_id, name, search_url, job_card_selector, title_selector, company_selector, job_url_selector, location_selector=None):
    conn = create_connection()
    success = False
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sites 
                SET name=?, search_url=?, job_card_selector=?, title_selector=?, company_selector=?, job_url_selector=?, location_selector=?
                WHERE id=?
            """, (name, search_url, job_card_selector, title_selector, company_selector, job_url_selector, location_selector, site_id))
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
                       s.title_selector, s.company_selector, s.job_url_selector, s.location_selector,
                       s.search_input_selector, s.expand_button_selector, s.is_career_directory
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

def add_company(name, careers_url, job_card_selector, title_selector, company_selector, job_url_selector, website=None, ats_type=None, ats_url=None, tech_stack=None, industry_category=None, countries=None):
    import datetime
    import json
    conn = create_connection()
    company_id = None
    if conn is not None:
        try:
            cursor = conn.cursor()
            date_added = datetime.datetime.now().isoformat()
            
            ts_str = json.dumps(tech_stack) if isinstance(tech_stack, list) else tech_stack
            cnt_str = json.dumps(countries) if isinstance(countries, list) else countries
            
            cursor.execute("""
                INSERT OR IGNORE INTO companies (name, careers_url, job_card_selector, title_selector, company_selector, job_url_selector, date_added, website, ats_type, ats_url, tech_stack, industry_category, countries)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, careers_url, job_card_selector, title_selector, company_selector, job_url_selector, date_added, website, ats_type, ats_url, ts_str, industry_category, cnt_str))
            conn.commit()
            company_id = cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding company: {e}")
        finally:
            conn.close()
    return company_id

def update_company(company_id, name, careers_url, job_card_selector, title_selector, company_selector, job_url_selector, website=None, ats_type=None, ats_url=None, tech_stack=None, industry_category=None, countries=None):
    import json
    conn = create_connection()
    success = False
    if conn is not None:
        try:
            cursor = conn.cursor()
            ts_str = json.dumps(tech_stack) if isinstance(tech_stack, list) else tech_stack
            cnt_str = json.dumps(countries) if isinstance(countries, list) else countries
            
            cursor.execute("""
                UPDATE companies 
                SET name=?, careers_url=?, job_card_selector=?, title_selector=?, company_selector=?, job_url_selector=?, website=?, ats_type=?, ats_url=?, tech_stack=?, industry_category=?, countries=?
                WHERE id=?
            """, (name, careers_url, job_card_selector, title_selector, company_selector, job_url_selector, website, ats_type, ats_url, ts_str, industry_category, cnt_str, company_id))
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

def reject_jobs_below_score(threshold):
    """Reject jobs that have a match score <= threshold."""
    conn = create_connection()
    updated_count = 0
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE jobs SET status = 'rejected' WHERE status = 'new' AND score <= ?", (threshold,))
            conn.commit()
            updated_count = cursor.rowcount
        except sqlite3.Error as e:
            print(f"Error rejecting jobs by score: {e}")
        finally:
            conn.close()
    return updated_count

def clean_blacklisted_companies_from_db(blacklist_file="blacklist.json"):
    """Delete companies from the database if their domain or name matches the blacklist."""
    from urllib.parse import urlparse
    import json
    
    if not os.path.exists(blacklist_file):
        print(f"[!] Blacklist file not found: {blacklist_file}")
        return 0
        
    with open(blacklist_file, "r", encoding="utf-8") as f:
        blacklist = json.load(f)
    if not isinstance(blacklist, list):
        return 0
    blacklist_set = {b.lower().strip() for b in blacklist if b}

    conn = create_connection()
    if conn is None:
        return 0
        
    deleted_count = 0
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, careers_url, ats_url FROM companies")
        rows = cursor.fetchall()
        
        ids_to_delete = []
        for cid, name, c_url, a_url in rows:
            url = c_url or a_url or ""
            is_bl = False
            if url:
                host = urlparse(url).netloc.lower().strip()
                if host and (host in blacklist_set or (host.startswith("www.") and host[4:] in blacklist_set)):
                    is_bl = True
                else:
                    parts = host.split(".")
                    for i in range(1, len(parts) - 1):
                        if ".".join(parts[i:]) in blacklist_set:
                            is_bl = True
                            break
            if not is_bl and name and name.lower().strip() in blacklist_set:
                is_bl = True
                
            if is_bl:
                ids_to_delete.append(cid)
                
        if ids_to_delete:
            cursor.executemany("DELETE FROM companies WHERE id = ?", [(i,) for i in ids_to_delete])
            conn.commit()
            deleted_count = len(ids_to_delete)
    except sqlite3.Error as e:
        print(f"Error cleaning blacklisted companies from DB: {e}")
    finally:
        conn.close()
        
    return deleted_count


# --- Profile Delivery Tracking Methods ---

def get_undelivered_jobs_for_profile(profile_id, min_score=0, limit=50, include_unscoped=True):
    """
    Fetch 'new' jobs that have not yet been delivered to `profile_id` and meet `min_score`.
    Also deduplicates against already-delivered jobs (and within the batch) by canonical URL
    and normalized (title, company) so rotated tracking query params never cause re-emails.
    """
    conn = create_connection()
    jobs = []
    if conn is not None:
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Build canonical keys of everything already delivered to this profile
            cursor.execute("""
                SELECT j.url, j.title, j.company
                FROM profile_deliveries pd
                JOIN jobs j ON j.id = pd.job_id
                WHERE pd.profile_id = ?
            """, (int(profile_id),))
            seen_urls = set()
            seen_tc = set()
            for row in cursor.fetchall():
                cu = canonicalize_job_url(row["url"])
                if cu:
                    seen_urls.add(cu)
                tc = _normalize_title_company(row["title"], row["company"])
                if tc:
                    seen_tc.add(tc)

            if include_unscoped:
                profile_clause = "(j.score_profile_id = ? OR j.score_profile_id IS NULL)"
            else:
                profile_clause = "j.score_profile_id = ?"
            cursor.execute(f"""
                SELECT j.*
                FROM jobs j
                WHERE j.status = 'new'
                  AND COALESCE(j.score, 0) >= ?
                  AND {profile_clause}
                  AND NOT EXISTS (
                      SELECT 1
                      FROM profile_deliveries pd
                      WHERE pd.profile_id = ? AND pd.job_id = j.id
                  )
                ORDER BY COALESCE(j.score, 0) DESC, j.id DESC
            """, (int(min_score), int(profile_id), int(profile_id)))

            for row in cursor.fetchall():
                item = dict(row)
                cu = canonicalize_job_url(item.get("url"))
                tc = _normalize_title_company(item.get("title"), item.get("company"))
                if (cu and cu in seen_urls) or (tc and tc in seen_tc):
                    continue
                if cu:
                    seen_urls.add(cu)
                if tc:
                    seen_tc.add(tc)
                jobs.append(item)
                if len(jobs) >= int(limit):
                    break
        except sqlite3.Error as e:
            print(f"Error fetching undelivered jobs for profile {profile_id}: {e}")
        finally:
            conn.close()
    return jobs


def record_profile_deliveries(profile_id, job_ids, run_id):
    """Idempotently record delivered job IDs for a profile. Returns count of newly inserted rows."""
    if not job_ids:
        return 0
    conn = create_connection()
    inserted = 0
    if conn is not None:
        try:
            cursor = conn.cursor()
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            for jid in job_ids:
                cursor.execute("""
                    INSERT OR IGNORE INTO profile_deliveries (profile_id, job_id, run_id, delivered_at)
                    VALUES (?, ?, ?, ?)
                """, (int(profile_id), int(jid), str(run_id), now))
                inserted += cursor.rowcount
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error recording profile deliveries: {e}")
        finally:
            conn.close()
    return inserted


def get_profile_delivery_stats(profile_id):
    """Return total delivered count and latest delivery timestamp for a profile."""
    conn = create_connection()
    stats = {"delivered_count": 0, "last_delivered_at": None}
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*), MAX(delivered_at)
                FROM profile_deliveries
                WHERE profile_id = ?
            """, (int(profile_id),))
            row = cursor.fetchone()
            if row:
                stats["delivered_count"] = row[0] or 0
                stats["last_delivered_at"] = row[1]
        except sqlite3.Error as e:
            print(f"Error fetching delivery stats: {e}")
        finally:
            conn.close()
    return stats


