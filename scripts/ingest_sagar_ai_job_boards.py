import os
import sys
import json
import sqlite3
import datetime

# Ensure project root in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)
from scripts.database import DB_PATH, create_connection

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

NEW_AI_JOB_BOARDS = {
    "AI Jobs": {
        "search_url": "https://aijobs.net/?q={search_term}",
        "job_card_selector": "div[class*='job'], li[class*='job'], article, a[href*='/hiring/jobs/'], tr",
        "title_selector": "h2, h3, a[href*='/jobs/'], a",
        "company_selector": "[class*='company'], span",
        "job_url_selector": "a[href*='/hiring/jobs/'], a[href*='/job/'], a",
        "location_selector": "[class*='location'], span"
    },
    "Himalayas Remote Jobs": {
        "search_url": "https://himalayas.app/jobs?q={search_term}",
        "job_card_selector": "[data-testid='job-card'], article, div[class*='JobCard'], div.border",
        "title_selector": "h2, h3, a[href*='/jobs/']",
        "company_selector": "a[href*='/companies/'], [class*='company']",
        "job_url_selector": "a[href*='/jobs/']",
        "location_selector": "[class*='location'], span"
    },
    "Cryptocurrency Jobs": {
        "search_url": "https://cryptocurrencyjobs.co/?query={search_term}",
        "job_card_selector": "li[class*='job'], article, div[class*='job-card']",
        "title_selector": "h2 a, h3 a, a[href*='/engineering/'], a[href*='/marketing/'], a",
        "company_selector": "[class*='company'], h3",
        "job_url_selector": "a[href*='/engineering/'], a[href*='/marketing/'], a[href*='/design/'], a[href*='/finance/'], a",
        "location_selector": "[class*='location'], span"
    },
    "Arc.dev Remote Jobs": {
        "search_url": "https://arc.dev/remote-jobs?search={search_term}",
        "job_card_selector": "div[class*='job-card'], div[class*='JobCard'], article, [data-testid*='job']",
        "title_selector": "h2, h3, a[href*='/remote-jobs/']",
        "company_selector": "[class*='company'], a[href*='/companies/']",
        "job_url_selector": "a[href*='/remote-jobs/']",
        "location_selector": "[class*='location'], span"
    },
    "NoDesk Remote Jobs": {
        "search_url": "https://nodesk.co/remote-jobs/",
        "job_card_selector": "tr, li[class*='job'], div[class*='job'], a[href*='/remote-jobs/']",
        "title_selector": "h2, h3, span, a",
        "company_selector": "[class*='company'], span",
        "job_url_selector": "a[href*='/remote-jobs/']",
        "location_selector": "[class*='location'], span"
    },
    "Welcome to the Jungle (Otta)": {
        "search_url": "https://www.welcometothejungle.com/en/jobs?query={search_term}&refinementList%5Boffices.country_code%5D%5B%5D=US",
        "job_card_selector": "article, div[data-testid='job-card'], li[class*='ais-Hits-item']",
        "title_selector": "h4, h3, a[href*='/jobs/']",
        "company_selector": "[data-testid='company-name'], [class*='company']",
        "job_url_selector": "a[href*='/jobs/']",
        "location_selector": "[class*='location'], span"
    },
    "Climatebase Jobs": {
        "search_url": "https://climatebase.org/jobs?q={search_term}",
        "job_card_selector": "div[class*='JobCard'], article, div[class*='job-card'], li",
        "title_selector": "h3, h2, a[href*='/job/']",
        "company_selector": "a[href*='/company/'], [class*='company']",
        "job_url_selector": "a[href*='/job/']",
        "location_selector": "[class*='location'], span"
    },
    "BuiltIn Remote Tech Jobs": {
        "search_url": "https://builtin.com/jobs/remote?search={search_term}",
        "job_card_selector": "[data-id='job-card'], div[class*='job-item'], div[id*='job-card']",
        "title_selector": "h2 a, a[data-id='job-card-title'], a[href*='/job/']",
        "company_selector": "[data-id='company-title'], [class*='company-name']",
        "job_url_selector": "a[data-id='job-card-title'], a[href*='/job/']",
        "location_selector": "[class*='location'], span"
    },
    "Techjobs": {
        "search_url": "https://techjobs.co/?s={search_term}",
        "job_card_selector": "article, div.job, li.job, [class*='job-card']",
        "title_selector": "h2, h3, a",
        "company_selector": "[class*='company']",
        "job_url_selector": "a",
        "location_selector": "[class*='location']"
    },
    "DailyRemote Software Jobs": {
        "search_url": "https://dailyremote.com/remote-software-development-jobs?search={search_term}",
        "job_card_selector": "article, div[class*='job-item'], [class*='job-card'], li",
        "title_selector": "h2, h3, a[href*='/remote-job/']",
        "company_selector": "[class*='company-name'], [class*='company']",
        "job_url_selector": "a[href*='/remote-job/']",
        "location_selector": "[class*='location'], span"
    },
    "TrueUp Jobs": {
        "search_url": "https://www.trueup.io/jobs?q={search_term}",
        "job_card_selector": "div[class*='card'], tr, div[class*='item'], article",
        "title_selector": "h3, h4, a[href*='/co/']",
        "company_selector": "[class*='company'], strong",
        "job_url_selector": "a[href*='/co/'], a",
        "location_selector": "[class*='location'], span"
    },
    "Post Job Free Tech": {
        "search_url": "https://www.postjobfree.com/jobs?q={search_term}&l=Remote",
        "job_card_selector": ".snippet, [class*='jobCard'], div[class*='item']",
        "title_selector": "h3 a, a[href*='/job/']",
        "company_selector": "[class*='company'], span.colorCompany",
        "job_url_selector": "a[href*='/job/']",
        "location_selector": "[class*='location'], span.colorLocation"
    },
    "Pangian Remote Community": {
        "search_url": "https://pangian.com/job-travel/?search_keywords={search_term}",
        "job_card_selector": "li.job_listing, div.job_listing, article",
        "title_selector": "h3, h4, a",
        "company_selector": "[class*='company']",
        "job_url_selector": "a",
        "location_selector": "[class*='location']"
    }
}

DIRECT_PLATFORM_COMPANIES = [
    {
        "name": "BuiltIn",
        "careers_url": "https://builtin.com/company/careers",
        "website": "https://builtin.com",
        "industry_category": "Tech Job Board & Media Platform",
        "ats_type": "greenhouse",
        "ats_url": "https://job-boards.greenhouse.io/builtin"
    },
    {
        "name": "Himalayas",
        "careers_url": "https://himalayas.app/",
        "website": "https://himalayas.app",
        "industry_category": "Remote Tech Job Board",
        "ats_type": None,
        "ats_url": None
    },
    {
        "name": "Cryptocurrency Jobs",
        "careers_url": "https://cryptocurrencyjobs.co/",
        "website": "https://cryptocurrencyjobs.co",
        "industry_category": "Web3 & Crypto Job Platform",
        "ats_type": None,
        "ats_url": None
    },
    {
        "name": "Arc.dev",
        "careers_url": "https://arc.dev/about",
        "website": "https://arc.dev",
        "industry_category": "Remote Developer Matching Network",
        "ats_type": None,
        "ats_url": None
    },
    {
        "name": "NoDesk",
        "careers_url": "https://nodesk.co/about/",
        "website": "https://nodesk.co",
        "industry_category": "Digital Nomad & Remote Work Platform",
        "ats_type": None,
        "ats_url": None
    },
    {
        "name": "Welcome to the Jungle (Otta)",
        "careers_url": "https://www.welcometothejungle.com/",
        "website": "https://www.welcometothejungle.com",
        "industry_category": "Curated Tech Job Recommendations",
        "ats_type": None,
        "ats_url": None
    },
    {
        "name": "Climatebase",
        "careers_url": "https://climatebase.org/about",
        "website": "https://climatebase.org",
        "industry_category": "Climate Tech Job Platform",
        "ats_type": None,
        "ats_url": None
    },
    {
        "name": "Techjobs",
        "careers_url": "https://techjobs.co/",
        "website": "https://techjobs.co",
        "industry_category": "Software Engineering Job Directory",
        "ats_type": None,
        "ats_url": None
    },
    {
        "name": "DailyRemote",
        "careers_url": "https://dailyremote.com/about",
        "website": "https://dailyremote.com",
        "industry_category": "Daily Curated Remote Job Directory",
        "ats_type": None,
        "ats_url": None
    },
    {
        "name": "TrueUp",
        "careers_url": "https://www.trueup.io/",
        "website": "https://www.trueup.io",
        "industry_category": "Tech Job Marketplace & Layoff Analytics",
        "ats_type": None,
        "ats_url": None
    },
    {
        "name": "PostJobFree",
        "careers_url": "https://www.postjobfree.com/",
        "website": "https://www.postjobfree.com",
        "industry_category": "Tech & Operations Job Aggregator",
        "ats_type": None,
        "ats_url": None
    },
    {
        "name": "Pangian",
        "careers_url": "https://pangian.com/",
        "website": "https://pangian.com",
        "industry_category": "Global Remote Professional Community",
        "ats_type": None,
        "ats_url": None
    }
]

DEAD_OR_SQUATTED_DOMAINS = [
    {
        "domain": "remoteimpact.io",
        "name": "Remote Impact",
        "url": "https://remoteimpact.io/",
        "reason": "EXPIRED_DOMAIN: Domain expired and squatted/hijacked by third-party streaming site.",
        "quarantined_at": datetime.datetime.now().isoformat()
    },
    {
        "domain": "remjobs.works",
        "name": "RemJobs",
        "url": "https://remjobs.works/",
        "reason": "HTTP_404: Endpoint unreachable / dead domain.",
        "quarantined_at": datetime.datetime.now().isoformat()
    }
]

def update_site_selectors_json():
    filepath = os.path.join(PROJECT_ROOT, "site_selectors.json")
    data = {}
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
    for k, v in NEW_AI_JOB_BOARDS.items():
        data[k] = v
        
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"[OK] Updated {filepath} with {len(NEW_AI_JOB_BOARDS)} boards.")

def update_job_search_sites_json():
    filepath = os.path.join(PROJECT_ROOT, "job_search_sites.json")
    data = {}
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            
    existing_names = {s.get("name") for s in data.get("job_search_sites", [])}
    added = 0
    for site_name, cfg in NEW_AI_JOB_BOARDS.items():
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
    
    # 1. Sync search boards to sites and search_configs
    print(f"[*] Syncing {len(NEW_AI_JOB_BOARDS)} search boards to SQLite...")
    sites_added = 0
    configs_added = 0
    
    for name, cfg in NEW_AI_JOB_BOARDS.items():
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
            
        cursor.execute("SELECT id FROM search_configs WHERE site_id = ?", (site_id,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO search_configs (site_id, search_terms, locations, filters)
                VALUES (?, ?, ?, ?)
            """, (site_id, json.dumps(DEFAULT_SEARCH_TERMS), json.dumps(DEFAULT_LOCATIONS), json.dumps({"job_type": "Full-time", "remote": True})))
            configs_added += 1

    # 2. Sync direct platform companies
    print(f"[*] Syncing {len(DIRECT_PLATFORM_COMPANIES)} platform companies to SQLite...")
    comp_added = 0
    comp_updated = 0
    for comp in DIRECT_PLATFORM_COMPANIES:
        cname = comp["name"]
        curl = comp["careers_url"]
        cat = comp.get("industry_category", "")
        ats = comp.get("ats_type")
        ats_url = comp.get("ats_url")
        website = comp.get("website", "")
        
        cursor.execute("SELECT id FROM companies WHERE LOWER(name) = LOWER(?) OR careers_url = ?", (cname, curl))
        row = cursor.fetchone()
        if row:
            cid = row[0]
            cursor.execute("""
                UPDATE companies
                SET careers_url = ?, industry_category = ?, ats_type = ?, ats_url = ?, website = ?
                WHERE id = ?
            """, (curl, cat, ats, ats_url, website, cid))
            comp_updated += 1
        else:
            cursor.execute("""
                INSERT INTO companies (name, careers_url, industry_category, ats_type, ats_url, website, date_added)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (cname, curl, cat, ats, ats_url, website))
            comp_added += 1
            
    conn.commit()
    conn.close()
    print(f"[OK] SQLite sync complete: {sites_added} sites added, {configs_added} configs added, {comp_added} companies added, {comp_updated} companies updated.")

def sync_base_companies_json():
    json_path = os.path.join(PROJECT_ROOT, "base_companies.json")
    existing_companies = []
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                existing_companies = json.load(f)
            except Exception:
                existing_companies = []
                
    existing_names = {c.get("name", "").lower(): i for i, c in enumerate(existing_companies)}
    existing_urls = {c.get("careers_url", "").lower(): i for i, c in enumerate(existing_companies)}
    
    added = 0
    updated = 0
    for comp in DIRECT_PLATFORM_COMPANIES:
        name = comp["name"]
        url = comp["careers_url"]
        cat = comp.get("industry_category", "Tech & Job Platforms")
        
        idx = existing_names.get(name.lower())
        if idx is None and url.lower() in existing_urls:
            idx = existing_urls[url.lower()]
            
        if idx is not None:
            existing_companies[idx]["careers_url"] = url
            existing_companies[idx]["category"] = cat
            updated += 1
        else:
            existing_companies.append({
                "name": name,
                "careers_url": url,
                "category": cat
            })
            added += 1
            
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(existing_companies, f, indent=2)
    print(f"[OK] Synced base_companies.json: {added} new entries added, {updated} updated.")

def quarantine_dead_domains():
    q_path = os.path.join(PROJECT_ROOT, "quarantined_domains.json")
    quarantined = []
    if os.path.exists(q_path):
        with open(q_path, "r", encoding="utf-8") as f:
            try:
                quarantined = json.load(f)
            except Exception:
                quarantined = []
                
    existing_domains = {q.get("domain", "").lower() for q in quarantined if isinstance(q, dict)}
    added = 0
    for dead in DEAD_OR_SQUATTED_DOMAINS:
        dom = dead["domain"].lower()
        if dom not in existing_domains:
            quarantined.append(dead)
            existing_domains.add(dom)
            added += 1
            print(f"    [QUARANTINED] {dead['name']} ({dom}): {dead['reason']}")
            
    with open(q_path, "w", encoding="utf-8") as f:
        json.dump(quarantined, f, indent=2)
    print(f"[OK] Updated quarantined_domains.json ({added} new quarantined domains).")

def main():
    print("=== TalentScout: Ingesting Sagar Vaghela's 15 High-Paying AI & Tech Job Boards ===")
    update_site_selectors_json()
    update_job_search_sites_json()
    sync_to_sqlite()
    sync_base_companies_json()
    quarantine_dead_domains()
    print("\n[SUCCESS] All high-paying AI & Tech job boards and platforms configured for auto_scour.py!")

if __name__ == "__main__":
    main()
