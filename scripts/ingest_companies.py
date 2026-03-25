import json
import sqlite3
import os
import sys

# Ensure imports work regardless of run location
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.database import add_company

def ingest_companies():
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "base_companies.json")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        companies = json.load(f)
        
    for c in companies:
        cname = c["name"]
        curl = c["careers_url"]
        
        # Add with empty selectors to trigger the smart fallback in auto_scour.py
        cid = add_company(
            name=cname,
            careers_url=curl,
            job_card_selector="",
            title_selector="",
            company_selector="",
            job_url_selector=""
        )
        if cid:
            print(f"[+] Added {cname} to trackers (ID: {cid})")
        else:
            print(f"[-] Skipped {cname} (Already exists or error)")

if __name__ == "__main__":
    ingest_companies()
