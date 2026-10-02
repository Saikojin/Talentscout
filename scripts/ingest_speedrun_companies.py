import os
import sys
import json
import sqlite3

# Ensure imports work regardless of run location
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.database import DB_PATH, create_connection

SPEEDRUN_COMPANIES = [
    {"name": "Chainguard", "slug": "chainguard", "category": "Security"},
    {"name": "Tailscale", "slug": "tailscale", "category": "Security"},
    {"name": "1Password", "slug": "1password", "category": "Security"},
    {"name": "Teleport", "slug": "teleport", "category": "Security"},
    {"name": "Onebrief", "slug": "onebrief", "category": "Security"},
    {"name": "Vanta", "slug": "vanta", "category": "Security"},
    {"name": "Beacon Biosignals", "slug": "beacon-biosignals", "category": "Healthtech"},
    {"name": "Maven Clinic", "slug": "maven-clinic", "category": "Healthtech"},
    {"name": "Freenome", "slug": "freenome", "category": "Healthtech"},
    {"name": "Honor", "slug": "honor", "category": "Healthtech"},
    {"name": "Viz.ai", "slug": "viz-ai", "category": "Healthtech"},
    {"name": "Mysten Labs", "slug": "mysten-labs", "category": "DevTools, Data & AI"},
    {"name": "Jellyfish", "slug": "jellyfish", "category": "DevTools, Data & AI"},
    {"name": "Cresta", "slug": "cresta", "category": "DevTools, Data & AI"},
    {"name": "Render", "slug": "render", "category": "DevTools, Data & AI"},
    {"name": "RunPod", "slug": "runpod", "category": "DevTools, Data & AI"},
    {"name": "PayNearMe", "slug": "paynearme", "category": "Fintech & Insurance"},
    {"name": "Affirm", "slug": "affirm", "category": "Fintech & Insurance"},
    {"name": "Upstart", "slug": "upstart", "category": "Fintech & Insurance"},
    {"name": "Vesta", "slug": "vesta", "category": "Fintech & Insurance"},
    {"name": "Lithic", "slug": "lithic", "category": "Fintech & Insurance"},
    {"name": "Fieldguide", "slug": "fieldguide", "category": "B2B SaaS"},
    {"name": "FirstWork", "slug": "firstwork", "category": "B2B SaaS"},
    {"name": "dili", "slug": "dili", "category": "B2B SaaS"},
    {"name": "ClassDojo", "slug": "classdojo", "category": "Consumer & Marketplaces"},
    {"name": "Reddit", "slug": "reddit", "category": "Consumer & Marketplaces"},
    {"name": "Pika", "slug": "pika", "category": "Consumer & Marketplaces"},
]

def ingest_speedrun_companies():
    conn = create_connection()
    cursor = conn.cursor()
    
    print(f"[*] Ingesting {len(SPEEDRUN_COMPANIES)} Speedrun employers into {DB_PATH}...")
    
    added_count = 0
    updated_count = 0
    
    for item in SPEEDRUN_COMPANIES:
        name = item["name"]
        slug = item["slug"]
        category = item["category"]
        careers_url = f"https://speedrun-talent-network.com/companies/{slug}"
        job_card_selector = "a.jb-row"
        title_selector = ".jb-title"
        company_selector = ""
        job_url_selector = "a.jb-row"
        location_selector = ".jb-meta"
        ats_type = "Speedrun"
        
        # Check if company exists by careers_url or exact name
        cursor.execute("SELECT id, name, careers_url FROM companies WHERE careers_url = ? OR name = ?", (careers_url, name))
        row = cursor.fetchone()
        
        if row:
            cid, existing_name, existing_url = row
            # Update selectors and URL to ensure latest Speedrun portal config
            cursor.execute("""
                UPDATE companies 
                SET careers_url = ?, job_card_selector = ?, title_selector = ?, company_selector = ?, 
                    job_url_selector = ?, location_selector = ?, industry_category = ?, ats_type = ?
                WHERE id = ?
            """, (careers_url, job_card_selector, title_selector, company_selector, job_url_selector, location_selector, category, ats_type, cid))
            updated_count += 1
            print(f"  [~] Updated {name} (ID: {cid}) -> {careers_url}")
        else:
            cursor.execute("""
                INSERT INTO companies (name, careers_url, job_card_selector, title_selector, company_selector, job_url_selector, location_selector, industry_category, ats_type, date_added)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (name, careers_url, job_card_selector, title_selector, company_selector, job_url_selector, location_selector, category, ats_type))
            added_count += 1
            print(f"  [+] Added {name} -> {careers_url}")
            
    conn.commit()
    conn.close()
    print(f"\n[OK] Companies Ingestion Complete: {added_count} added, {updated_count} updated.")

def update_base_companies_json():
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
    for item in SPEEDRUN_COMPANIES:
        url = f"https://speedrun-talent-network.com/companies/{item['slug']}"
        if url not in existing_urls and item["name"] not in existing_names:
            existing_companies.append({
                "name": item["name"],
                "careers_url": url,
                "category": item["category"],
                "location": "Remote"
            })
            added += 1
            
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(existing_companies, f, indent=2)
    print(f"[OK] Synced base_companies.json ({added} new entries added).")

if __name__ == "__main__":
    ingest_speedrun_companies()
    update_base_companies_json()
