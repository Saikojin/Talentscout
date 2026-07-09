import urllib.request
import json
import os
import sys

# Ensure imports work regardless of run location
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.database import add_company

OPENJOBS_JSON_URL = "https://raw.githubusercontent.com/outscal/OpenJobs/main/data/companies_v2.json"

def parse_ats_type(ats_links):
    if not ats_links:
        return None, None
    
    # Try to find a valid link
    primary_link = ats_links[0]
    link_lower = primary_link.lower()
    
    ats_types = ["greenhouse", "lever", "ashby", "workable", "smartrecruiters", "workday", "teamtailor", "recruitee", "bamboohr", "breezy", "jobvite", "join", "personio"]
    for t in ats_types:
        if t in link_lower:
            return t, primary_link
            
    return None, primary_link

def main():
    print(f"[*] Downloading OpenJobs dataset from {OPENJOBS_JSON_URL}...")
    try:
        req = urllib.request.Request(
            OPENJOBS_JSON_URL, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"[!] Error downloading dataset: {e}")
        sys.exit(1)
        
    print(f"[*] Successfully downloaded {len(data)} companies.")
    print("[*] Ingesting into database (Option B: all records, no filtering)...")
    
    added_count = 0
    
    for idx, c in enumerate(data):
        name = c.get("name")
        website = c.get("website")
        ats_links = c.get("ats_links", [])
        tech_stack = c.get("tech_stack", [])
        industry_category = c.get("industry_category")
        countries = c.get("countries", [])
        
        # Determine careers_url/ats_url
        ats_type, ats_url = parse_ats_type(ats_links)
        
        # If no ats_links, default careers_url to website/careers or website itself
        if not ats_url:
            careers_url = website.rstrip('/') + '/careers' if website else f"http://unknown-careers-{idx}.com"
        else:
            careers_url = ats_url
            
        # Add to DB
        cid = add_company(
            name=name,
            careers_url=careers_url,
            job_card_selector="",
            title_selector="",
            company_selector="",
            job_url_selector="",
            website=website,
            ats_type=ats_type,
            ats_url=ats_url,
            tech_stack=tech_stack,
            industry_category=industry_category,
            countries=countries
        )
        if cid:
            added_count += 1
            
        if (idx + 1) % 1000 == 0:
            print(f"  [-] Processed {idx + 1}/{len(data)} companies...")
            
    print(f"\n[*] Ingestion complete! Added {added_count} new companies to the database.")

if __name__ == "__main__":
    main()
