import os
import sys
import json
import sqlite3

# Ensure imports work regardless of run location
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.database import DB_PATH, create_connection

ZAPIER_PARTNERS = [
    {
        "name": "123FormBuilder",
        "careers_url": "https://apply.workable.com/123formbuilder/",
        "ats_type": "workable",
        "ats_url": "https://apply.workable.com/123formbuilder/",
        "category": "SaaS & Automation",
        "location": "Remote / Timisoara, Romania"
    },
    {
        "name": "Kit",
        "careers_url": "https://jobs.ashbyhq.com/kit",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/kit",
        "category": "Creator Tools & Email Marketing",
        "location": "Remote"
    },
    {
        "name": "AccuLynx",
        "careers_url": "https://acculynx.com/careers/",
        "job_card_selector": "a[href*='recruiting.paylocity.com']",
        "title_selector": "a",
        "job_url_selector": "a",
        "location_selector": "",
        "category": "Vertical SaaS & Construction CRM",
        "location": "Chicago, IL / Remote"
    },
    {
        "name": "Knack",
        "careers_url": "https://www.knack.com/careers/",
        "category": "No-Code & Database Apps",
        "location": "Remote"
    },
    {
        "name": "ActiveCampaign",
        "careers_url": "https://jobs.lever.co/activecampaign",
        "ats_type": "lever",
        "ats_url": "https://jobs.lever.co/activecampaign",
        "category": "Marketing Automation & CRM",
        "location": "Chicago, IL / Remote"
    },
    {
        "name": "Landbot",
        "careers_url": "https://jobs.landbot.io/jobs",
        "job_card_selector": "a[href*='/jobs/']",
        "title_selector": "span, div",
        "job_url_selector": "a",
        "location_selector": "",
        "category": "Chatbots & Conversational UI",
        "location": "Barcelona, Spain / Remote"
    },
    {
        "name": "Airtable",
        "careers_url": "https://boards.greenhouse.io/airtable",
        "ats_type": "greenhouse",
        "ats_url": "https://boards.greenhouse.io/airtable",
        "category": "Collaboration & Low-Code Databases",
        "location": "San Francisco, CA / Remote"
    },
    {
        "name": "Miro",
        "careers_url": "https://jobs.ashbyhq.com/miro",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/miro",
        "category": "Visual Collaboration & Whiteboarding",
        "location": "San Francisco, CA / Amsterdam / Remote"
    },
    {
        "name": "Apollo",
        "careers_url": "https://job-boards.greenhouse.io/apolloio",
        "ats_type": "greenhouse",
        "ats_url": "https://job-boards.greenhouse.io/apolloio",
        "category": "Sales Intelligence & Engagement",
        "location": "Remote"
    },
    {
        "name": "Nutshell",
        "careers_url": "https://www.nutshell.com/careers",
        "category": "CRM & Sales Automation",
        "location": "Ann Arbor, MI / Remote"
    },
    {
        "name": "BambooHR",
        "careers_url": "https://www.bamboohr.com/careers/",
        "category": "HR & People Operations",
        "location": "Lindon, UT / Remote"
    },
    {
        "name": "One Signal",
        "careers_url": "https://onesignal.com/careers",
        "category": "Omnichannel Messaging & Push Notifications",
        "location": "San Mateo, CA / Remote"
    },
    {
        "name": "Bitly",
        "careers_url": "https://bitly.com/pages/careers",
        "category": "Link Management & Analytics",
        "location": "New York, NY / Remote"
    },
    {
        "name": "Pandadoc",
        "careers_url": "https://boards.greenhouse.io/pandadoc",
        "ats_type": "greenhouse",
        "ats_url": "https://boards.greenhouse.io/pandadoc",
        "category": "Document Automation & E-Signatures",
        "location": "San Francisco, CA / Remote"
    },
    {
        "name": "Brevo",
        "careers_url": "https://jobs.lever.co/brevo",
        "ats_type": "lever",
        "ats_url": "https://jobs.lever.co/brevo",
        "category": "CRM & Digital Marketing",
        "location": "Paris, France / Remote"
    },
    {
        "name": "Patreon",
        "careers_url": "https://jobs.ashbyhq.com/patreon",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/patreon",
        "category": "Creator Economy & Subscriptions",
        "location": "San Francisco, CA / New York / Remote"
    },
    {
        "name": "Calendly",
        "careers_url": "https://boards.greenhouse.io/calendly",
        "ats_type": "greenhouse",
        "ats_url": "https://boards.greenhouse.io/calendly",
        "category": "Scheduling & Productivity",
        "location": "Atlanta, GA / Remote"
    },
    {
        "name": "Pipedrive",
        "careers_url": "https://www.pipedrive.com/en/jobs/open-positions",
        "category": "Sales CRM & Pipeline Management",
        "location": "Tallinn, Estonia / New York / Remote"
    },
    {
        "name": "ClickUp",
        "careers_url": "https://jobs.ashbyhq.com/clickup",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/clickup",
        "category": "Productivity & Project Management",
        "location": "San Diego, CA / Remote"
    },
    {
        "name": "Service Titan",
        "careers_url": "https://servicetitan.wd1.myworkdayjobs.com/ServiceTitan",
        "ats_type": "workday",
        "ats_url": "https://servicetitan.wd1.myworkdayjobs.com/ServiceTitan",
        "category": "Field Service Management SaaS",
        "location": "Glendale, CA / Remote"
    },
    {
        "name": "Copper CRM",
        "careers_url": "https://coppercrm.applytojob.com/apply",
        "category": "Google Workspace CRM",
        "location": "San Francisco, CA / Remote"
    },
    {
        "name": "Stan",
        "careers_url": "https://stanforcreators.notion.site/Stan-Job-Board-b8430f3ca1d44c46b8ba74d5434ff022",
        "category": "Creator Store & Digital Products",
        "location": "Remote"
    },
    {
        "name": "Discord",
        "careers_url": "https://boards.greenhouse.io/discord",
        "ats_type": "greenhouse",
        "ats_url": "https://boards.greenhouse.io/discord",
        "category": "Voice, Video & Community Chat",
        "location": "San Francisco, CA / Remote"
    },
    {
        "name": "Stripe",
        "careers_url": "https://boards.greenhouse.io/stripe",
        "ats_type": "greenhouse",
        "ats_url": "https://boards.greenhouse.io/stripe",
        "category": "Payments & Financial Infrastructure",
        "location": "San Francisco, CA / Dublin / Remote"
    },
    {
        "name": "Eventbrite",
        "careers_url": "https://jobs.bendingspoons.com/positions",
        "job_card_selector": "a[href*='/positions/']",
        "title_selector": "div, h3",
        "job_url_selector": "a[href*='/positions/']",
        "location_selector": "",
        "category": "Ticketing & Event Management",
        "location": "Milan, Italy / San Francisco / Remote"
    },
    {
        "name": "Survey Monkey",
        "careers_url": "https://jobs.ashbyhq.com/surveymonkey",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/surveymonkey",
        "category": "Feedback & Survey Software",
        "location": "San Mateo, CA / Remote"
    },
    {
        "name": "Ghost",
        "careers_url": "https://careers.ghost.org/",
        "category": "Open Source Publishing & Newsletters",
        "location": "Remote"
    },
    {
        "name": "Tawk.to",
        "careers_url": "https://tawk-to.breezy.hr/",
        "ats_type": "breezy",
        "ats_url": "https://tawk-to.breezy.hr/",
        "category": "Live Chat & Customer Communication",
        "location": "Remote"
    },
    {
        "name": "Help Scout",
        "careers_url": "https://jobs.ashbyhq.com/helpscout",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/helpscout",
        "category": "Help Desk & Customer Support",
        "location": "Remote"
    },
    {
        "name": "Teachable",
        "careers_url": "https://boards.greenhouse.io/teachablecareers",
        "ats_type": "greenhouse",
        "ats_url": "https://boards.greenhouse.io/teachablecareers",
        "category": "Online Courses & Creator Monetization",
        "location": "New York, NY / Remote"
    },
    {
        "name": "Intuit",
        "careers_url": "https://jobs.intuit.com/search-jobs",
        "job_card_selector": "section#search-results-list ul li",
        "title_selector": "h2",
        "job_url_selector": "a",
        "location_selector": ".job-location",
        "category": "Financial & Tax Software",
        "location": "Mountain View, CA / Remote"
    },
    {
        "name": "Toggl",
        "careers_url": "https://toggl.com/jobs/",
        "category": "Time Tracking & Productivity",
        "location": "Remote"
    },
    {
        "name": "Jobber",
        "careers_url": "https://jobs.ashbyhq.com/jobber",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/jobber",
        "category": "Home Service Operations Software",
        "location": "Edmonton, Canada / Remote"
    },
    {
        "name": "Trello",
        "careers_url": "https://www.atlassian.com/company/careers",
        "category": "Visual Work Management & Collaboration",
        "location": "Sydney, Australia / San Francisco / Remote"
    },
    {
        "name": "Kajabi",
        "careers_url": "https://www.kajabi.com/careers",
        "category": "All-in-One Creator Platform",
        "location": "Irvine, CA / Remote"
    },
    {
        "name": "Zendesk",
        "careers_url": "https://zendesk.wd1.myworkdayjobs.com/zendesk",
        "ats_type": "workday",
        "ats_url": "https://zendesk.wd1.myworkdayjobs.com/zendesk",
        "category": "Customer Service & Engagement Platform",
        "location": "San Francisco, CA / Remote"
    }
]

def ingest_zapier_partners():
    conn = create_connection()
    cursor = conn.cursor()
    
    print(f"[*] Ingesting {len(ZAPIER_PARTNERS)} Zapier partner employers into {DB_PATH}...")
    
    added_count = 0
    updated_count = 0
    
    for item in ZAPIER_PARTNERS:
        name = item["name"]
        careers_url = item["careers_url"]
        category = item.get("category", "SaaS & Automation")
        job_card_selector = item.get("job_card_selector", "")
        title_selector = item.get("title_selector", "")
        company_selector = item.get("company_selector", "")
        job_url_selector = item.get("job_url_selector", "")
        location_selector = item.get("location_selector", "")
        ats_type = item.get("ats_type", "")
        ats_url = item.get("ats_url", "")
        
        # Check if company exists by careers_url or exact name
        cursor.execute("SELECT id, name, careers_url FROM companies WHERE careers_url = ? OR name = ?", (careers_url, name))
        row = cursor.fetchone()
        
        if row:
            cid, existing_name, existing_url = row
            cursor.execute("""
                UPDATE companies 
                SET name = ?, careers_url = ?, job_card_selector = ?, title_selector = ?, company_selector = ?, 
                    job_url_selector = ?, location_selector = ?, industry_category = ?, ats_type = ?, ats_url = ?
                WHERE id = ?
            """, (name, careers_url, job_card_selector, title_selector, company_selector, job_url_selector, 
                  location_selector, category, ats_type, ats_url, cid))
            updated_count += 1
            print(f"  [~] Updated {name} (ID: {cid}) -> {careers_url} [ATS: {ats_type or 'Direct'}]")
        else:
            cursor.execute("""
                INSERT INTO companies (name, careers_url, job_card_selector, title_selector, company_selector, 
                                        job_url_selector, location_selector, industry_category, ats_type, ats_url, date_added)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (name, careers_url, job_card_selector, title_selector, company_selector, job_url_selector, 
                  location_selector, category, ats_type, ats_url))
            added_count += 1
            print(f"  [+] Added {name} -> {careers_url} [ATS: {ats_type or 'Direct'}]")
            
    conn.commit()
    conn.close()
    print(f"\n[OK] Zapier Partners Ingestion Complete: {added_count} added, {updated_count} updated.")

def update_base_companies_json():
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "base_companies.json")
    existing_companies = []
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                existing_companies = json.load(f)
            except Exception:
                existing_companies = []
                
    existing_names = {c.get("name").lower().strip() for c in existing_companies if c.get("name")}
    existing_urls = {c.get("careers_url").lower().strip() for c in existing_companies if c.get("careers_url")}
    
    added = 0
    updated = 0
    
    for item in ZAPIER_PARTNERS:
        name_lower = item["name"].lower().strip()
        url_lower = item["careers_url"].lower().strip()
        
        # Check if already present in base_companies
        found_idx = None
        for idx, ex in enumerate(existing_companies):
            if ex.get("name", "").lower().strip() == name_lower or ex.get("careers_url", "").lower().strip() == url_lower:
                found_idx = idx
                break
                
        entry = {
            "name": item["name"],
            "careers_url": item["careers_url"],
            "category": item.get("category", "SaaS & Automation"),
            "location": item.get("location", "Remote")
        }
        if item.get("ats_type"):
            entry["ats_type"] = item["ats_type"]
            entry["ats_url"] = item["ats_url"]
        if item.get("job_card_selector"):
            entry["job_card_selector"] = item["job_card_selector"]
            entry["title_selector"] = item.get("title_selector", "")
            entry["job_url_selector"] = item.get("job_url_selector", "")
            
        if found_idx is not None:
            existing_companies[found_idx].update(entry)
            updated += 1
        else:
            existing_companies.append(entry)
            added += 1
            
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(existing_companies, f, indent=2)
    print(f"[OK] Synced base_companies.json ({added} new entries added, {updated} updated).")

if __name__ == "__main__":
    ingest_zapier_partners()
    update_base_companies_json()
