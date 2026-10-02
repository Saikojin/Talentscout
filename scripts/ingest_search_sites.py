import os
import sys
import json
import sqlite3

# Ensure imports work regardless of run location
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.database import DB_PATH, create_connection, add_site, add_search_config

NEW_SITES_SELECTORS = {
    "SpeedrunTalentNetwork": {
        "search_url": "https://speedrun-talent-network.com/jobs?remote=1&scope=everywhere&search={search_term}",
        "job_card_selector": "a.jb-row",
        "title_selector": ".jb-title",
        "company_selector": ".jb-meta",
        "job_url_selector": "a.jb-row",
        "location_selector": ".jb-meta"
    },
    "ArcDev": {
        "search_url": "https://arc.dev/remote-jobs?query={search_term}",
        "job_card_selector": ".job-card",
        "title_selector": ".job-title",
        "company_selector": ".company-name",
        "job_url_selector": "a.job-title",
        "location_selector": ".location-info"
    },
    "Wellfound": {
        "search_url": "https://wellfound.com/jobs?q={search_term}",
        "job_card_selector": "[data-test='JobListItem']",
        "title_selector": "a[data-test='JobTitle']",
        "company_selector": "[data-test='StartupName']",
        "job_url_selector": "a[data-test='JobTitle']",
        "location_selector": "[data-test='JobLocation']"
    },
    "PowerToFly": {
        "search_url": "https://powertofly.com/jobs/?keywords={search_term}&location=Remote",
        "job_card_selector": ".job-card",
        "title_selector": ".job-title a",
        "company_selector": ".company-title",
        "job_url_selector": ".job-title a",
        "location_selector": ".job-location"
    },
    "AuthenticJobs": {
        "search_url": "https://authenticjobs.com/?search={search_term}",
        "job_card_selector": "article.job",
        "title_selector": "h3.title a",
        "company_selector": "div.company a",
        "job_url_selector": "h3.title a",
        "location_selector": "span.location"
    }
}

DEFAULT_SEARCH_TERMS = [
    "Senior QA Engineer",
    "SDET",
    "Senior Test Engineer",
    "QA",
    "Automation Engineer",
    "AI",
    "Test Automation Architect"
]

DEFAULT_LOCATIONS = [
    "Remote",
    "Seattle, WA",
    "Redmond, WA"
]

def update_site_selectors_json():
    filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site_selectors.json")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for k, v in NEW_SITES_SELECTORS.items():
        data[k] = v
        
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"[OK] Updated {filepath} with {len(NEW_SITES_SELECTORS)} new site selectors.")

def update_job_search_sites_json():
    filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "job_search_sites.json")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    existing_names = {s.get("name") for s in data.get("job_search_sites", [])}
    
    for site_name, cfg in NEW_SITES_SELECTORS.items():
        if site_name not in existing_names:
            data.setdefault("job_search_sites", []).append({
                "name": site_name,
                "url": cfg["search_url"].split("?")[0],
                "search_terms": DEFAULT_SEARCH_TERMS,
                "locations": DEFAULT_LOCATIONS,
                "filters": {
                    "job_type": "Full-time",
                    "remote": True
                }
            })
            
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[OK] Updated {filepath}.")

def sync_to_database():
    conn = create_connection()
    cursor = conn.cursor()
    
    for site_name, cfg in NEW_SITES_SELECTORS.items():
        cursor.execute("SELECT id FROM sites WHERE name = ?", (site_name,))
        row = cursor.fetchone()
        
        if row:
            site_id = row[0]
            cursor.execute("""
                UPDATE sites 
                SET search_url = ?, job_card_selector = ?, title_selector = ?, 
                    company_selector = ?, job_url_selector = ?, location_selector = ?
                WHERE id = ?
            """, (cfg["search_url"], cfg["job_card_selector"], cfg["title_selector"], 
                  cfg["company_selector"], cfg["job_url_selector"], cfg.get("location_selector", ""), site_id))
            print(f"  [~] Updated site record in DB: {site_name} (ID: {site_id})")
        else:
            site_id = add_site(
                name=site_name,
                search_url=cfg["search_url"],
                job_card_selector=cfg["job_card_selector"],
                title_selector=cfg["title_selector"],
                company_selector=cfg["company_selector"],
                job_url_selector=cfg["job_url_selector"],
                location_selector=cfg.get("location_selector", "")
            )
            print(f"  [+] Added site record to DB: {site_name} (ID: {site_id})")
            
        # Ensure search configs exist
        cursor.execute("SELECT id FROM search_configs WHERE site_id = ?", (site_id,))
        if not cursor.fetchone():
            add_search_config(
                site_id=site_id,
                search_terms=DEFAULT_SEARCH_TERMS,
                locations=DEFAULT_LOCATIONS,
                filters={"remote": True}
            )
            print(f"    [+] Added search config for {site_name}")
            
    conn.close()
    print("[OK] Synchronized sites & search_configs with job_tracker.db.")

if __name__ == "__main__":
    update_site_selectors_json()
    update_job_search_sites_json()
    sync_to_database()
