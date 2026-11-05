import os
import sys
import json
import sqlite3

# Ensure imports work regardless of run location
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.database import DB_PATH, create_connection, add_site, add_search_config, add_company

GETRO_SELECTORS = {
    "job_card_selector": "[data-testid='job-list-item'], .job-list-job, .job-card",
    "title_selector": "[data-testid='job-title-link'], h2.job-list-job-title a, a[href*='/jobs/'], a[href*='/job/']",
    "company_selector": "a.job-list-job-company-link, a[href*='/companies/'], [itemprop='hiringOrganization']",
    "job_url_selector": "[data-testid='job-title-link'], h2.job-list-job-title a, a[href*='/jobs/'], a[href*='/job/']",
    "location_selector": "[itemprop='jobLocation'], .job-list-badges, [class*='location']"
}

NEW_SEARCH_BOARDS = {
    # VC Firm Job Boards (Getro / Mendel / Consider)
    "a16z Portfolio Jobs": {
        "search_url": "https://portfoliojobs.a16z.com/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "Sequoia Capital Jobs": {
        "search_url": "https://jobs.sequoiacap.com/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "General Catalyst Jobs": {
        "search_url": "https://jobs.generalcatalyst.com/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "Khosla Ventures Jobs": {
        "search_url": "https://jobs.khoslaventures.com/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "Kleiner Perkins Jobs": {
        "search_url": "https://jobs.kleinerperkins.com/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "Accel Jobs": {
        "search_url": "https://jobs.accel.com/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "Lightspeed Jobs": {
        "search_url": "https://jobs.lsvp.com/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "Thrive Capital Jobs": {
        "search_url": "https://jobs.thrivecap.com/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "Bessemer Venture Partners Jobs": {
        "search_url": "https://jobs.bvp.com/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "Felicis Ventures Jobs": {
        "search_url": "https://jobs.felicis.com/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "Lux Capital Jobs": {
        "search_url": "https://jobs.luxcapital.com/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "Contrary Capital Jobs": {
        "search_url": "https://jobs.contrary.com/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "Battery Ventures Jobs": {
        "search_url": "https://jobs.battery.com/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "NEA Jobs": {
        "search_url": "https://careers.nea.com/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "Insight Partners Jobs": {
        "search_url": "https://jobs.insightpartners.com/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "Menlo Ventures Jobs": {
        "search_url": "https://jobs.menlovc.com/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "Bain Capital Ventures Jobs": {
        "search_url": "https://jobs.baincapitalventures.com/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "Notable Capital Jobs": {
        "search_url": "https://jobs.ggvc.com/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "Antler Jobs": {
        "search_url": "https://careers.antler.co/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "BITKRAFT Ventures Jobs": {
        "search_url": "https://careers.bitkraft.vc/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "8VC Jobs": {
        "search_url": "https://jobs.8vc.com/jobs?q={search_term}&locations={location}",
        **GETRO_SELECTORS
    },
    "CRV Consider": {
        "search_url": "https://consider.com/boards/crv?q={search_term}",
        "job_card_selector": "[data-testid='job-row'], [class*='job'], div.row",
        "title_selector": "a[href*='/job'], h3",
        "company_selector": "[class*='company']",
        "job_url_selector": "a[href*='/job']",
        "location_selector": "[class*='location']"
    },
    "Greylock Portfolio Jobs": {
        "search_url": "https://greylock.com/jobs/portfolio-jobs/?query={search_term}",
        "job_card_selector": "div[class*='job'], div.row, [class*='card']",
        "title_selector": "a[href*='job=']",
        "company_selector": "a[href*='/companies/'], h4, h5",
        "job_url_selector": "a[href*='job='], a[href*='lever.co'], a[href*='greenhouse.io']",
        "location_selector": "[class*='location'], span"
    },
    "Index Ventures Startup Jobs": {
        "search_url": "https://www.indexventures.com/startup-jobs?search={search_term}",
        "job_card_selector": "[class*='job-item'], [class*='jobCard'], tr, div.border",
        "title_selector": "a[href*='/jobs/'], h3",
        "company_selector": "a[href*='/companies/']",
        "job_url_selector": "a[href*='/jobs/']",
        "location_selector": "[class*='location'], span"
    },
    "Pear VC Jobs (Ashby)": {
        "search_url": "https://jobs.ashbyhq.com/Pear-VC",
        "job_card_selector": "a[href*='/Pear-VC/']",
        "title_selector": "h3, span",
        "company_selector": "h2, h1",
        "job_url_selector": "a[href*='/Pear-VC/']",
        "location_selector": "[class*='location'], p"
    },
    # Startup Aggregators
    "YC Work at a Startup": {
        "search_url": "https://www.workatastartup.com/jobs/v2?query={search_term}",
        "job_card_selector": "a[href*='/jobs/']:not([href*='role'])",
        "title_selector": "h3, span.variant2-wipe",
        "company_selector": "p.font-semibold",
        "job_url_selector": "a[href*='/jobs/']:not([href*='role'])",
        "location_selector": "p.line-clamp-2"
    },
    "Top Startups": {
        "search_url": "https://topstartups.io/jobs/?q={search_term}",
        "job_card_selector": "div.card.card-body#item-card-filter",
        "title_selector": "#job-title, h5",
        "company_selector": "#startup-website-link h7, a[href*='utm_source=topstartups'] h7",
        "job_url_selector": "a[href*='jobs.ashbyhq.com'], a[href*='greenhouse.io'], a[href*='lever.co'], a:has(#job-title)",
        "location_selector": "h7:has(i.fa-map-marker-alt)"
    },
    "Startups Gallery": {
        "search_url": "https://startups.gallery",
        "job_card_selector": "[class*='card'], [class*='startup'], a[href*='/company/']",
        "title_selector": "h3, h4",
        "company_selector": "h2, h3",
        "job_url_selector": "a[href*='/company/'], a[href*='/jobs/']",
        "location_selector": "[class*='location']"
    },
    "OutGeek Women in Tech": {
        "search_url": "https://outgeek.org",
        "job_card_selector": "[class*='job'], [class*='card'], article",
        "title_selector": "h2, h3, a",
        "company_selector": "[class*='company']",
        "job_url_selector": "a[href*='/job/'], a",
        "location_selector": "[class*='location']"
    }
}

DEFAULT_SEARCH_TERMS = [
    "Senior QA Engineer",
    "SDET",
    "Senior Test Engineer",
    "QA",
    "Automation Engineer",
    "AI",
    "Test Automation Architect",
    "Full Stack Developer",
    "Python Engineer"
]

DEFAULT_LOCATIONS = [
    "Remote",
    "Seattle, WA",
    "Redmond, WA"
]

DIRECT_COMPANIES_AND_FELLOWSHIPS = [
    {
        "name": "Speedrun Product Engineer (Jordan Mazer)",
        "careers_url": "https://speedrun-talent-network.com/product-engineer/",
        "industry_category": "Venture & Startups",
        "ats_type": "Speedrun"
    },
    {
        "name": "Neo Scholars",
        "careers_url": "https://neo.com/scholars",
        "industry_category": "Fellowship & Mentorship",
        "ats_type": "Direct"
    },
    {
        "name": "Z Fellows",
        "careers_url": "https://www.zfellows.com/",
        "industry_category": "Fellowship & Accelerator",
        "ats_type": "Direct"
    },
    {
        "name": "Kleiner Perkins Fellows",
        "careers_url": "https://www.kleinerperkins.com/fellows/",
        "industry_category": "Fellowship & Accelerator",
        "ats_type": "Direct"
    },
    {
        "name": "Pear Fellows",
        "careers_url": "https://pear.vc/fellows/",
        "industry_category": "Fellowship & Accelerator",
        "ats_type": "Direct"
    },
    {
        "name": "a16z College Talent",
        "careers_url": "https://a16z.com/college-talent/",
        "industry_category": "Talent Network",
        "ats_type": "Direct"
    },
    {
        "name": "Underdog.io",
        "careers_url": "https://underdog.io/",
        "industry_category": "Startup Talent Network",
        "ats_type": "Direct"
    },
    {
        "name": "Cosign",
        "careers_url": "https://cosign.co/",
        "industry_category": "Startup Talent Network",
        "ats_type": "Direct"
    },
    {
        "name": "Jobbie",
        "careers_url": "https://jobbie.bot/",
        "industry_category": "AI Job Search Agent",
        "ats_type": "Direct"
    }
]

CURATED_NEWSLETTERS = [
    {"name": "job hunting sux (Jordan Mazer)", "url": "https://www.jobhuntingsux.com/", "feed": ""},
    {"name": "a16z Jobs", "url": "https://a16zjobs.substack.com/", "feed": "https://a16zjobs.substack.com/feed"},
    {"name": "Ali Rohde Jobs", "url": "https://alirohdejobs.substack.com/", "feed": "https://alirohdejobs.substack.com/feed"},
    {"name": "next play", "url": "https://nextplayso.substack.com/", "feed": "https://nextplayso.substack.com/feed"},
    {"name": "Nonlinear News", "url": "https://nonlinearnews.com/", "feed": ""},
    {"name": "Beyond Bay St.", "url": "https://beyondbayst.substack.com/", "feed": "https://beyondbayst.substack.com/feed"},
    {"name": "Why You Should Join", "url": "https://whyyoushouldjoin.substack.com/", "feed": "https://whyyoushouldjoin.substack.com/feed"},
    {"name": "Web of Jobs", "url": "https://webofjobs.substack.com/", "feed": "https://webofjobs.substack.com/feed"}
]

def update_site_selectors_json():
    filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site_selectors.json")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for k, v in NEW_SEARCH_BOARDS.items():
        data[k] = v
        
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"[OK] Updated {filepath} with {len(NEW_SEARCH_BOARDS)} boards.")

def update_job_search_sites_json():
    filepath = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "job_search_sites.json")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    existing_names = {s.get("name") for s in data.get("job_search_sites", [])}
    added = 0
    for site_name, cfg in NEW_SEARCH_BOARDS.items():
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
    print(f"[*] Syncing {len(NEW_SEARCH_BOARDS)} search boards to SQLite...")
    sites_added = 0
    configs_added = 0
    
    for name, cfg in NEW_SEARCH_BOARDS.items():
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
            
    # 2. Sync direct companies and fellowships
    print(f"[*] Syncing {len(DIRECT_COMPANIES_AND_FELLOWSHIPS)} fellowships & direct companies to SQLite...")
    comp_added = 0
    for comp in DIRECT_COMPANIES_AND_FELLOWSHIPS:
        cname = comp["name"]
        curl = comp["careers_url"]
        cat = comp.get("industry_category", "")
        ats = comp.get("ats_type", "")
        
        cursor.execute("SELECT id FROM companies WHERE careers_url = ? OR name = ?", (curl, cname))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO companies (name, careers_url, job_card_selector, title_selector, company_selector, job_url_selector, industry_category, ats_type, date_added)
                VALUES (?, ?, '', '', '', '', ?, ?, datetime('now'))
            """, (cname, curl, cat, ats))
            comp_added += 1
            
    conn.commit()
    conn.close()
    print(f"[OK] SQLite sync complete: {sites_added} sites added, {configs_added} configs added, {comp_added} companies added.")

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
    for item in DIRECT_COMPANIES_AND_FELLOWSHIPS:
        name = item["name"]
        url = item["careers_url"]
        if url not in existing_urls and name not in existing_names:
            existing_companies.append({
                "name": name,
                "careers_url": url,
                "category": item.get("industry_category", "Startups & Fellowships")
            })
            added += 1
            
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(existing_companies, f, indent=2)
    print(f"[OK] Synced base_companies.json ({added} new entries added).")

def save_newsletters_metadata():
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "newsletters_to_scour.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(CURATED_NEWSLETTERS, f, indent=2)
    print(f"[OK] Saved {len(CURATED_NEWSLETTERS)} curated newsletters to {json_path}.")

def main():
    print("=== TalentScout: Ingesting LinkedIn Post Startup & VC Sources ===")
    update_site_selectors_json()
    update_job_search_sites_json()
    sync_to_sqlite()
    sync_base_companies_json()
    save_newsletters_metadata()
    print("\n[SUCCESS] All LinkedIn sources successfully configured for auto_scour.py!")

if __name__ == "__main__":
    main()
