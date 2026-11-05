import os
import sys
import json
import sqlite3

# Ensure imports work regardless of run location
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.database import DB_PATH, create_connection

GAMEDEV_SEARCH_BOARDS = {
    "ASGC (All Star Games Careers)": {
        "search_url": "https://jobs.asgc.gg/",
        "job_card_selector": "tr.border-b, tbody tr",
        "title_selector": "td:nth-child(3)",
        "company_selector": "td:nth-child(1)",
        "job_url_selector": "a[href*='http']:has-text('Apply'), a[href*='http']",
        "location_selector": "td:nth-child(6), td:nth-child(7), td:nth-child(8)"
    },
    "Games Jobs Index": {
        "search_url": "https://gamesjobsindex.com/?q={search_term}",
        "job_card_selector": "li.vgj-card-item",
        "title_selector": ".vgj-card-title",
        "company_selector": ".vgj-card-studio",
        "job_url_selector": ".vgj-card",
        "location_selector": ".vgj-card-location, .vgj-card-body"
    },
    "Hitmarker": {
        "search_url": "https://hitmarker.net/jobs?keyword={search_term}",
        "job_card_selector": "article.job-feed-card, [class*='job-feed-card']",
        "title_selector": "h3",
        "company_selector": "span.truncate.font-medium, div:has(> span.font-slab) span.truncate",
        "job_url_selector": "a[href*='/jobs/']",
        "location_selector": "div.flex.gap-x-1.5 span.truncate, div.text-alpha-6, span:has-text('USA'), span:has-text('Remote')"
    },
    "DevQuest": {
        "search_url": "https://devquest.gg/?q={search_term}",
        "job_card_selector": ".rtop, div:has(> .rmain)",
        "title_selector": "a.title",
        "company_selector": ".studio",
        "job_url_selector": "a.title",
        "location_selector": ".loc, [class*='loc'], .studioline"
    },
    "Games Jobs Direct": {
        "search_url": "https://www.gamesjobsdirect.com/",
        "job_card_selector": "a.slick-slide, [class*='slick-slide']",
        "title_selector": "strong, h3, h4",
        "company_selector": "span, p",
        "job_url_selector": "a[href*='/job/']",
        "location_selector": "span, p"
    },
    "Remote Game Jobs": {
        "search_url": "https://remotegamejobs.com/search?q={search_term}",
        "job_card_selector": "a.card, a.has-text-black",
        "title_selector": ".body .title, strong",
        "company_selector": ".body .sub, small",
        "job_url_selector": "a.card, a.has-text-black",
        "location_selector": ".body .row, span.tag"
    },
    "Work With Indies": {
        "search_url": "https://www.workwithindies.com/search?query={search_term}",
        "job_card_selector": "div.search-result-item, a.job-card",
        "title_selector": "a.search-title, .job-card-title, h3",
        "company_selector": ".job-card-text.bold, a.search-title",
        "job_url_selector": "a.search-title, a.job-card",
        "location_selector": ".job-card-text, .search-result-item"
    }
}

DEFAULT_SEARCH_TERMS = [
    "Senior QA Engineer",
    "SDET",
    "QA",
    "Automation Engineer",
    "Game Tester",
    "QA Tester",
    "Test Automation Architect",
    "Game Developer",
    "Python Engineer"
]

DEFAULT_LOCATIONS = [
    "Remote",
    "Seattle, WA",
    "Redmond, WA"
]

CURATED_GAME_STUDIOS = [
    {"name": "4A Games", "careers_url": "https://www.4a-games.com.mt/careers", "category": "Gaming (AAA)"},
    {"name": "4J Studios", "careers_url": "https://4jstudios.com/careers/", "category": "Gaming (Console)"},
    {"name": "Arcanaut Studios", "careers_url": "https://www.arcanautstudios.com/careers", "category": "Gaming (Indie)"},
    {"name": "Archetype Entertainment", "careers_url": "https://www.archetype-entertainment.com/en-US", "category": "Gaming (AAA Sci-Fi)"},
    {"name": "Awaceb", "careers_url": "https://www.awaceb.com/", "category": "Gaming (Indie)"},
    {"name": "BKOM Studios", "careers_url": "https://jobs.bkom.com/", "category": "Gaming (Full-Service)"},
    {"name": "Blowfish Studios", "careers_url": "https://www.blowfishstudios.com/careers", "category": "Gaming (Multi-platform)"},
    {"name": "Bossa Studios", "careers_url": "https://www.bossagames.com/jobs", "category": "Gaming (Simulation/Indie)"},
    {"name": "Cyanide Studios", "careers_url": "https://cyanide-studio.com/en/join-us/", "category": "Gaming (RPG/Action)"},
    {"name": "Deck Nine Games", "careers_url": "https://www.deckninegames.com/careers", "category": "Gaming (Narrative)"},
    {"name": "Enduring Games", "careers_url": "https://enduring.games/jobs/", "category": "Gaming (Co-dev)"},
    {"name": "Crytek", "careers_url": "https://www.crytek.com/career", "category": "Gaming & Engine (CryEngine)"},
    {"name": "Virtuos", "careers_url": "https://www.virtuosgames.com/careers/", "category": "Gaming (Co-dev)"},
    {"name": "Keywords Studios", "careers_url": "https://www.keywordsstudios.com/careers/", "category": "Gaming (QA & Localization)"},
    {"name": "Scopely", "careers_url": "https://scopely.com/join-us/", "category": "Gaming (Mobile & Cross-platform)"},
    {"name": "Riot Games", "careers_url": "https://www.riotgames.com/en/work-with-us", "category": "Gaming (Esports & AAA)"},
    {"name": "Light & Wonder", "careers_url": "https://www.lnw.com/careers/", "category": "Gaming & Casino Tech"},
    {"name": "Sony PlayStation Studios", "careers_url": "https://www.playstation.com/en-us/corporate/playstation-jobs/", "category": "Gaming (PlayStation)"},
    {"name": "Super Spline Studios", "careers_url": "https://supersplinestudios.com/careers/", "category": "Gaming (Animation)"},
    {"name": "Roboto Games", "careers_url": "https://robotogames.com/careers", "category": "Gaming (Multiplayer)"},
    {"name": "iam8bit", "careers_url": "https://www.iam8bit.com/pages/careers", "category": "Gaming & Publishing"}
]

def update_site_selectors_json():
    filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site_selectors.json")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for k, v in GAMEDEV_SEARCH_BOARDS.items():
        data[k] = v
        
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"[OK] Updated {filepath} with {len(GAMEDEV_SEARCH_BOARDS)} gamedev boards.")

def update_job_search_sites_json():
    filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "job_search_sites.json")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    existing_names = {s.get("name") for s in data.get("job_search_sites", [])}
    added = 0
    for site_name, cfg in GAMEDEV_SEARCH_BOARDS.items():
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
            added += 1
            
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"[OK] Updated {filepath} ({added} new entries added).")

def sync_to_sqlite():
    conn = create_connection()
    cursor = conn.cursor()
    
    # 1. Sync sites and search_configs
    print(f"[*] Syncing {len(GAMEDEV_SEARCH_BOARDS)} gamedev search boards to SQLite...")
    sites_added = 0
    sites_updated = 0
    configs_added = 0
    
    for name, cfg in GAMEDEV_SEARCH_BOARDS.items():
        # Check if site exists
        cursor.execute("SELECT id FROM sites WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            site_id = row[0]
            cursor.execute("""
                UPDATE sites 
                SET search_url = ?, job_card_selector = ?, title_selector = ?, company_selector = ?, job_url_selector = ?, location_selector = ?
                WHERE id = ?
            """, (cfg["search_url"], cfg["job_card_selector"], cfg["title_selector"], cfg["company_selector"], cfg["job_url_selector"], cfg.get("location_selector", ""), site_id))
            sites_updated += 1
        else:
            cursor.execute("""
                INSERT INTO sites (name, search_url, job_card_selector, title_selector, company_selector, job_url_selector, location_selector)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, cfg["search_url"], cfg["job_card_selector"], cfg["title_selector"], cfg["company_selector"], cfg["job_url_selector"], cfg.get("location_selector", "")))
            site_id = cursor.lastrowid
            sites_added += 1
            
        # Ensure search_config exists for this site
        cursor.execute("SELECT id FROM search_configs WHERE site_id = ?", (site_id,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO search_configs (site_id, search_terms, locations, filters)
                VALUES (?, ?, ?, ?)
            """, (site_id, json.dumps(DEFAULT_SEARCH_TERMS), json.dumps(DEFAULT_LOCATIONS), json.dumps({"job_type": "Full-time", "remote": True})))
            configs_added += 1
            
    # 2. Sync direct game studios to companies table
    print(f"[*] Syncing {len(CURATED_GAME_STUDIOS)} game studios to SQLite companies table...")
    comp_added = 0
    for comp in CURATED_GAME_STUDIOS:
        cname = comp["name"]
        curl = comp["careers_url"]
        cat = comp.get("category", "Gaming")
        
        cursor.execute("SELECT id FROM companies WHERE careers_url = ? OR name = ?", (curl, cname))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO companies (name, careers_url, job_card_selector, title_selector, company_selector, job_url_selector, industry_category, ats_type, date_added)
                VALUES (?, ?, '', '', '', '', ?, 'Direct', datetime('now'))
            """, (cname, curl, cat))
            comp_added += 1
            
    conn.commit()
    conn.close()
    print(f"[OK] SQLite sync complete: {sites_added} sites added, {sites_updated} updated, {configs_added} configs added, {comp_added} game studios added.")

def sync_base_companies_json():
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "base_companies.json")
    existing_companies = []
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                existing_companies = json.load(f)
            except Exception:
                existing_companies = []
                
    existing_urls = {c.get("careers_url") for c in existing_companies}
    existing_names = {c.get("name") for c in existing_companies}
    
    added = 0
    for item in CURATED_GAME_STUDIOS:
        name = item["name"]
        url = item["careers_url"]
        if url not in existing_urls and name not in existing_names:
            existing_companies.append({
                "name": name,
                "careers_url": url,
                "category": item.get("category", "Gaming")
            })
            added += 1
            
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(existing_companies, f, indent=2)
    print(f"[OK] Synced base_companies.json ({added} new entries added).")

def main():
    print("=== TalentScout: Ingesting Game Dev Job Sources ===")
    update_site_selectors_json()
    update_job_search_sites_json()
    sync_to_sqlite()
    sync_base_companies_json()
    print("\n[SUCCESS] All 7 Game Dev Job Sources successfully configured for auto_scour.py!")

if __name__ == "__main__":
    main()
