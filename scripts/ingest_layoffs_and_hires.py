"""
TalentScout — Layoffs & Hires Ingestion and Sync Engine
Ingests companies, direct career/ATS portals, and search configurations from
https://layoffsandhires.com/ into TalentScout's auto_scour ecosystem.
"""

import argparse
import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from typing import Dict, Any, List, Optional, Tuple

# Ensure project root in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from scripts.database import create_connection
except ImportError:
    print("Error importing database module. Make sure you run from project root.")
    sys.exit(1)

SITE_NAME = "Layoffs & Hires"
SITE_BASE_URL = "https://layoffsandhires.com/"
COMPANIES_JSON_URL = "https://layoffsandhires.com/search/companies.json"
FEED_JSON_URL = "https://layoffsandhires.com/feed.json"
SEARCH_TOKEN_URL_TEMPLATE = "https://layoffsandhires.com/search/t/{prefix}.json"

DEFAULT_SEARCH_TERMS = [
    "Senior QA Engineer",
    "SDET",
    "Senior Test Engineer",
    "QA",
    "Automation Engineer",
    "AI",
    "Python Engineer"
]

DEFAULT_LOCATIONS = [
    "Remote",
    "Seattle, WA",
    "Redmond, WA"
]

LAYOFFS_HIRES_CONFIG: Dict[str, Any] = {
    "search_url": "https://layoffsandhires.com/",
    "search_input_selector": "input[type='search'], input[placeholder*='Search']",
    "expand_button_selector": "button.matches-more",
    "job_card_selector": "section.matches ol.matches-list li",
    "title_selector": "span.matches-name",
    "company_selector": "span.matches-name",
    "job_url_selector": "a",
    "location_selector": "",
    "is_career_directory": True,
    "max_cards": 60
}

ATS_HOST_MAP = {
    "greenhouse.io": "greenhouse",
    "myworkdayjobs.com": "workday",
    "lever.co": "lever",
    "ashbyhq.com": "ashby",
    "workable.com": "workable",
    "smartrecruiters.com": "smartrecruiters",
    "bamboohr.com": "bamboohr",
    "recruitee.com": "recruitee",
    "teamtailor.com": "teamtailor",
    "jobvite.com": "jobvite",
    "personio.de": "personio",
    "personio.com": "personio",
    "join.com": "join"
}


def log(msg: str):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {msg}")


def detect_ats_type(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Detects ATS type and normalizes ats_url from a career portal link.
    Returns (ats_type, ats_url).
    """
    if not url:
        return None, None
    url_lower = url.lower()
    for host, ats in ATS_HOST_MAP.items():
        if host in url_lower:
            return ats, url
    return None, None


def fetch_remote_json(url: str, timeout: int = 15) -> Any:
    """Fetch JSON data from a remote endpoint with browser-like user agent."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def update_site_selectors_json(dry_run: bool = False) -> bool:
    """Updates site_selectors.json with the Layoffs & Hires configuration."""
    filepath = os.path.join(PROJECT_ROOT, "site_selectors.json")
    data: Dict[str, Any] = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            log(f"[!] Warning reading {filepath}: {e}")

    data[SITE_NAME] = LAYOFFS_HIRES_CONFIG

    if not dry_run:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        log(f"[OK] Saved Layoffs & Hires configuration to {filepath}")
    else:
        log(f"[DRY RUN] Would update {filepath} with {SITE_NAME}")
    return True


def update_job_search_sites_json(dry_run: bool = False) -> bool:
    """Updates job_search_sites.json with Layoffs & Hires search terms and locations."""
    filepath = os.path.join(PROJECT_ROOT, "job_search_sites.json")
    data: Dict[str, Any] = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            log(f"[!] Warning reading {filepath}: {e}")

    sites_list = data.setdefault("job_search_sites", [])
    existing_idx = None
    for idx, s in enumerate(sites_list):
        if s.get("name") == SITE_NAME:
            existing_idx = idx
            break

    entry = {
        "name": SITE_NAME,
        "url": SITE_BASE_URL,
        "search_terms": DEFAULT_SEARCH_TERMS,
        "locations": DEFAULT_LOCATIONS,
        "filters": {
            "job_type": "Full-time",
            "is_career_directory": True
        }
    }

    if existing_idx is not None:
        sites_list[existing_idx] = entry
    else:
        sites_list.append(entry)

    if not dry_run:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        log(f"[OK] Saved Layoffs & Hires search profile to {filepath}")
    else:
        log(f"[DRY RUN] Would update {filepath} with {SITE_NAME}")
    return True


def sync_site_to_sqlite(dry_run: bool = False) -> Tuple[int, int]:
    """Syncs Layoffs & Hires to SQLite sites and search_configs tables."""
    conn = create_connection()
    if not conn:
        log("[!] Could not connect to SQLite database.")
        return 0, 0

    cursor = conn.cursor()
    # Check if sites table has our custom columns
    cursor.execute("PRAGMA table_info(sites)")
    site_cols = {col[1] for col in cursor.fetchall()}

    cursor.execute("SELECT id FROM sites WHERE name = ?", (SITE_NAME,))
    row = cursor.fetchone()
    site_id = None

    if row:
        site_id = row[0]
        if not dry_run:
            update_fields = [
                "search_url = ?",
                "job_card_selector = ?",
                "title_selector = ?",
                "company_selector = ?",
                "job_url_selector = ?",
                "location_selector = ?"
            ]
            params = [
                LAYOFFS_HIRES_CONFIG["search_url"],
                LAYOFFS_HIRES_CONFIG["job_card_selector"],
                LAYOFFS_HIRES_CONFIG["title_selector"],
                LAYOFFS_HIRES_CONFIG["company_selector"],
                LAYOFFS_HIRES_CONFIG["job_url_selector"],
                LAYOFFS_HIRES_CONFIG.get("location_selector", "")
            ]

            if "search_input_selector" in site_cols:
                update_fields.append("search_input_selector = ?")
                params.append(LAYOFFS_HIRES_CONFIG["search_input_selector"])
            if "expand_button_selector" in site_cols:
                update_fields.append("expand_button_selector = ?")
                params.append(LAYOFFS_HIRES_CONFIG["expand_button_selector"])
            if "is_career_directory" in site_cols:
                update_fields.append("is_career_directory = ?")
                params.append(1 if LAYOFFS_HIRES_CONFIG.get("is_career_directory") else 0)

            params.append(site_id)
            sql = f"UPDATE sites SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(sql, tuple(params))
            log(f"[OK] Updated existing site entry in SQLite (site_id={site_id})")
    else:
        if not dry_run:
            insert_cols = ["name", "search_url", "job_card_selector", "title_selector", "company_selector", "job_url_selector", "location_selector"]
            insert_vals = [
                SITE_NAME,
                LAYOFFS_HIRES_CONFIG["search_url"],
                LAYOFFS_HIRES_CONFIG["job_card_selector"],
                LAYOFFS_HIRES_CONFIG["title_selector"],
                LAYOFFS_HIRES_CONFIG["company_selector"],
                LAYOFFS_HIRES_CONFIG["job_url_selector"],
                LAYOFFS_HIRES_CONFIG.get("location_selector", "")
            ]
            if "search_input_selector" in site_cols:
                insert_cols.append("search_input_selector")
                insert_vals.append(LAYOFFS_HIRES_CONFIG["search_input_selector"])
            if "expand_button_selector" in site_cols:
                insert_cols.append("expand_button_selector")
                insert_vals.append(LAYOFFS_HIRES_CONFIG["expand_button_selector"])
            if "is_career_directory" in site_cols:
                insert_cols.append("is_career_directory")
                insert_vals.append(1 if LAYOFFS_HIRES_CONFIG.get("is_career_directory") else 0)

            placeholders = ", ".join(["?"] * len(insert_cols))
            sql = f"INSERT INTO sites ({', '.join(insert_cols)}) VALUES ({placeholders})"
            cursor.execute(sql, tuple(insert_vals))
            site_id = cursor.lastrowid
            log(f"[OK] Created new site entry in SQLite (site_id={site_id})")

    # Sync search_configs
    configs_added = 0
    if site_id:
        cursor.execute("SELECT id FROM search_configs WHERE site_id = ?", (site_id,))
        if not cursor.fetchone():
            if not dry_run:
                cursor.execute("""
                    INSERT INTO search_configs (site_id, search_terms, locations, filters)
                    VALUES (?, ?, ?, ?)
                """, (
                    site_id,
                    json.dumps(DEFAULT_SEARCH_TERMS),
                    json.dumps(DEFAULT_LOCATIONS),
                    json.dumps({"job_type": "Full-time", "is_career_directory": True})
                ))
                configs_added = 1
                log(f"[OK] Created search_config entry for site_id={site_id}")
        else:
            log(f"[*] search_config entry already exists for site_id={site_id}")

    if not dry_run:
        conn.commit()
    conn.close()
    return (1 if site_id else 0), configs_added


def ingest_companies_catalog(max_count: Optional[int] = None, dry_run: bool = False) -> Dict[str, int]:
    """
    Downloads companies.json from layoffsandhires.com and ingests them into:
    1. base_companies.json
    2. SQLite companies table (with automatic ATS classification)
    """
    log(f"[*] Downloading companies catalog from {COMPANIES_JSON_URL}...")
    try:
        data = fetch_remote_json(COMPANIES_JSON_URL)
    except Exception as e:
        log(f"[!] Failed to fetch companies catalog: {e}")
        return {"fetched": 0, "added_json": 0, "added_db": 0}

    companies_raw = data.get("companies", [])
    log(f"[*] Received {len(companies_raw)} companies from Layoffs & Hires catalog.")

    if max_count:
        companies_raw = companies_raw[:max_count]

    # Load existing base_companies.json
    base_comp_path = os.path.join(PROJECT_ROOT, "base_companies.json")
    existing_companies = []
    if os.path.exists(base_comp_path):
        try:
            with open(base_comp_path, "r", encoding="utf-8") as f:
                existing_companies = json.load(f)
        except Exception:
            existing_companies = []

    existing_names = {c.get("name", "").lower(): i for i, c in enumerate(existing_companies)}
    existing_urls = {c.get("careers_url", "").lower(): i for i, c in enumerate(existing_companies) if c.get("careers_url")}

    json_added = 0
    json_updated = 0

    conn = create_connection()
    cursor = conn.cursor() if conn else None

    # Check companies table columns
    comp_cols = set()
    if cursor:
        cursor.execute("PRAGMA table_info(companies)")
        comp_cols = {col[1] for col in cursor.fetchall()}

    db_added = 0
    db_updated = 0

    for item in companies_raw:
        if not isinstance(item, list) or len(item) < 3:
            continue
        slug, display_name, careers_url = item[0], item[1], item[2]
        ats_type, ats_url = detect_ats_type(careers_url)

        # 1. Update/Add in base_companies.json structure
        target_idx = existing_names.get(display_name.lower())
        if target_idx is None and careers_url.lower() in existing_urls:
            target_idx = existing_urls[careers_url.lower()]

        comp_dict = {
            "name": display_name,
            "careers_url": careers_url,
            "category": f"LayoffsAndHires Catalog ({ats_type.upper() if ats_type else 'Direct'})"
        }
        if ats_type:
            comp_dict["ats_type"] = ats_type
            comp_dict["ats_url"] = ats_url

        if target_idx is not None:
            existing_companies[target_idx].update(comp_dict)
            json_updated += 1
        else:
            existing_companies.append(comp_dict)
            existing_names[display_name.lower()] = len(existing_companies) - 1
            existing_urls[careers_url.lower()] = len(existing_companies) - 1
            json_added += 1

        # 2. Update/Add in SQLite companies table
        if cursor and not dry_run:
            cursor.execute("SELECT id FROM companies WHERE careers_url = ?", (careers_url,))
            row = cursor.fetchone()
            if row:
                cid = row[0]
                cursor.execute("""
                    UPDATE companies
                    SET name = ?, ats_type = COALESCE(?, ats_type), ats_url = COALESCE(?, ats_url)
                    WHERE id = ?
                """, (display_name, ats_type, ats_url, cid))
                db_updated += 1
            else:
                cursor.execute("SELECT id FROM companies WHERE LOWER(name) = LOWER(?)", (display_name,))
                row_name = cursor.fetchone()
                if row_name:
                    cid = row_name[0]
                    try:
                        cursor.execute("""
                            UPDATE companies
                            SET careers_url = ?, ats_type = COALESCE(?, ats_type), ats_url = COALESCE(?, ats_url)
                            WHERE id = ?
                        """, (careers_url, ats_type, ats_url, cid))
                        db_updated += 1
                    except sqlite3.IntegrityError:
                        pass
                else:
                    try:
                        cursor.execute("""
                            INSERT INTO companies (name, careers_url, ats_type, ats_url, date_added)
                            VALUES (?, ?, ?, ?, datetime('now'))
                        """, (display_name, careers_url, ats_type, ats_url))
                        db_added += 1
                    except sqlite3.IntegrityError:
                        pass

    if not dry_run:
        with open(base_comp_path, "w", encoding="utf-8") as f:
            json.dump(existing_companies, f, indent=2)
        if conn:
            conn.commit()

    if conn:
        conn.close()

    log(f"[OK] Synced {len(companies_raw)} companies: {json_added} new in JSON ({json_updated} updated), {db_added} new in DB ({db_updated} updated).")
    return {
        "fetched": len(companies_raw),
        "json_added": json_added,
        "json_updated": json_updated,
        "db_added": db_added,
        "db_updated": db_updated
    }


def query_hiring_for_term(term: str) -> List[Dict[str, Any]]:
    """
    Simulates the layoffsandhires.com search algorithm offline/API-direct:
    1. Fetches /search/companies.json
    2. Maps tokens via /search/t/{prefix}.json
    3. Builds matching company list with direct career URLs pre-populated with ?q={term}
    """
    cleaned_term = term.strip().lower()
    if not cleaned_term:
        return []

    words = re.findall(r'[a-z0-9+#]+', cleaned_term)
    if not words:
        return []

    # Map words to 2-char prefix
    def to_prefix(w: str) -> str:
        s = re.sub(r'[^a-z0-9]', '_', w[:2])
        return s.ljust(2, '_')

    prefixes = list({to_prefix(w) for w in words})
    log(f"[*] Querying Layoffs & Hires inverted indices for prefixes: {prefixes}...")

    # Load companies catalog
    comp_data = fetch_remote_json(COMPANIES_JSON_URL)
    companies = comp_data.get("companies", [])

    # Load inverted index for each prefix
    token_indices: Dict[str, Dict[str, Any]] = {}
    for p in prefixes:
        url = SEARCH_TOKEN_URL_TEMPLATE.format(prefix=p)
        try:
            token_indices[p] = fetch_remote_json(url)
        except Exception:
            token_indices[p] = {}

    # Intersect/accumulate matches
    matched_companies: Dict[int, Dict[str, Any]] = {}
    for w in words:
        p = to_prefix(w)
        idx_data = token_indices.get(p, {})
        token_hits = idx_data.get(w, {})
        for comp_id_str, postings in token_hits.items():
            try:
                comp_id = int(comp_id_str)
            except ValueError:
                continue
            if comp_id >= len(companies):
                continue

            if comp_id not in matched_companies:
                matched_companies[comp_id] = {
                    "company_id": comp_id,
                    "name": companies[comp_id][1],
                    "raw_url": companies[comp_id][2],
                    "jobs": set(),
                    "term_hits": 0
                }

            entry = matched_companies[comp_id]
            entry["term_hits"] += 1
            for post_val in postings:
                entry["jobs"].add(post_val >> 3)

    results = []
    q_encoded = urllib.parse.quote(term.strip())
    for comp_id, entry in matched_companies.items():
        raw_url = entry["raw_url"]
        # If workday jobs, append ?q=query just like the official site JS does
        if ".myworkdayjobs.com/" in raw_url:
            career_url = f"{raw_url}?q={q_encoded}"
        else:
            career_url = raw_url

        ats_type, _ = detect_ats_type(career_url)
        results.append({
            "name": entry["name"],
            "url": career_url,
            "jobs_count": len(entry["jobs"]),
            "term_hits": entry["term_hits"],
            "ats_type": ats_type
        })

    # Sort by term hits descending, then job count descending
    results.sort(key=lambda x: (x["term_hits"], x["jobs_count"]), reverse=True)
    return results


def main():
    parser = argparse.ArgumentParser(description="Layoffs & Hires Sync & Ingestion Engine")
    parser.add_argument("--sync-all", action="store_true", help="Sync site selectors, search configs, and full companies catalog")
    parser.add_argument("--sync-config", action="store_true", help="Sync site_selectors.json, job_search_sites.json, and SQLite sites/search_configs")
    parser.add_argument("--sync-companies", action="store_true", help="Download and sync all 3,462+ companies into base_companies.json and SQLite")
    parser.add_argument("--search", type=str, help="Search for companies hiring for a specific term (e.g. 'QA', 'SDET')")
    parser.add_argument("--limit", type=int, default=None, help="Max items to display/process (default: all for sync, 30 for search)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without modifying database or files")

    args = parser.parse_args()

    if not any([args.sync_all, args.sync_config, args.sync_companies, args.search]):
        parser.print_help()
        return

    if args.sync_all or args.sync_config:
        log("=== Step 1: Syncing Layoffs & Hires Configuration ===")
        update_site_selectors_json(dry_run=args.dry_run)
        update_job_search_sites_json(dry_run=args.dry_run)
        sync_site_to_sqlite(dry_run=args.dry_run)

    if args.sync_all or args.sync_companies:
        log("\n=== Step 2: Ingesting Layoffs & Hires Companies Catalog ===")
        ingest_companies_catalog(max_count=args.limit, dry_run=args.dry_run)

    if args.search:
        log(f"\n=== Searching Layoffs & Hires for: '{args.search}' ===")
        hits = query_hiring_for_term(args.search)
        search_limit = args.limit or 30
        log(f"[*] Found {len(hits)} companies actively hiring for '{args.search}':")
        for i, hit in enumerate(hits[:search_limit], 1):
            ats_str = f"[{hit['ats_type']}] " if hit['ats_type'] else ""
            print(f"  {i:2d}. {hit['name']} ({hit['jobs_count']} jobs) {ats_str}-> {hit['url']}")


if __name__ == "__main__":
    main()
