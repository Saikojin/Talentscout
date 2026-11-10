import os
import sys
import json
import sqlite3
import datetime

# Ensure project root in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)
from scripts.database import DB_PATH, create_connection

AI_REMOTE_COMPANIES = [
    {
        "name": "Skild AI",
        "careers_url": "https://www.skild.ai/career",
        "website": "https://www.skild.ai",
        "industry_category": "Robotics & Physical AI",
        "ats_type": None,
        "ats_url": None,
        "job_card_selector": "[class*='job'], [class*='career'], li, tr, article",
        "title_selector": "a, h2, h3, h4",
        "job_url_selector": "a",
        "location_selector": "[class*='location'], span"
    },
    {
        "name": "Syllo",
        "careers_url": "https://syllo.ai/",
        "website": "https://syllo.ai/",
        "industry_category": "Legaltech & Applied AI",
        "ats_type": "greenhouse",
        "ats_url": "https://job-boards.greenhouse.io/syllo",
        "job_card_selector": "[data-testid='job-list-item'], .job-card, .opening",
        "title_selector": "a[href*='/jobs/'], h3",
        "job_url_selector": "a[href*='/jobs/']",
        "location_selector": ".location, [class*='location']"
    },
    {
        "name": "microagi",
        "careers_url": "https://www.microagi.ai",
        "website": "https://www.microagi.ai",
        "industry_category": "Embodied AI & Industrial Robotics",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/microagi",
        "job_card_selector": "a[href*='/microagi/']",
        "title_selector": "h3, span",
        "job_url_selector": "a[href*='/microagi/']",
        "location_selector": "p, [class*='location']"
    },
    {
        "name": "Nova Intelligence",
        "careers_url": "https://www.novaintelligence.com/careers",
        "website": "https://www.novaintelligence.com",
        "industry_category": "Enterprise AI & ERP Systems",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/novaintelligence",
        "job_card_selector": "a[href*='/novaintelligence/']",
        "title_selector": "h3, span",
        "job_url_selector": "a[href*='/novaintelligence/']",
        "location_selector": "p, [class*='location']"
    },
    {
        "name": "Nous Research",
        "careers_url": "https://nousresearch.com/",
        "website": "https://nousresearch.com/",
        "industry_category": "Open-Source LLMs & AI Research",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/nousresearch",
        "job_card_selector": "a[href*='/nousresearch/']",
        "title_selector": "h3, span",
        "job_url_selector": "a[href*='/nousresearch/']",
        "location_selector": "p, [class*='location']"
    },
    {
        "name": "Glow",
        "careers_url": "https://www.glowcyber.com/",
        "website": "https://www.glowcyber.com/",
        "industry_category": "Agentic Endpoint Security",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/glow",
        "job_card_selector": "a[href*='/glow/']",
        "title_selector": "h3, span",
        "job_url_selector": "a[href*='/glow/']",
        "location_selector": "p, [class*='location']"
    },
    {
        "name": "Fluidstack",
        "careers_url": "https://fluidstack.io/",
        "website": "https://fluidstack.io/",
        "industry_category": "AI Compute Infrastructure & Data Centers",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/fluidstack",
        "job_card_selector": "a[href*='/fluidstack/']",
        "title_selector": "h3, span",
        "job_url_selector": "a[href*='/fluidstack/']",
        "location_selector": "p, [class*='location']"
    },
    {
        "name": "ElevenLabs",
        "careers_url": "https://elevenlabs.io/careers",
        "website": "https://elevenlabs.io",
        "industry_category": "AI Voice & Audio Foundation Models",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/elevenlabs",
        "job_card_selector": "a[href*='/elevenlabs/'], a[href*='/ElevenLabs/']",
        "title_selector": "h3, span",
        "job_url_selector": "a[href*='/elevenlabs/'], a[href*='/ElevenLabs/']",
        "location_selector": "p, [class*='location']"
    },
    {
        "name": "Onyx Security",
        "careers_url": "https://www.onyx.security/careers",
        "website": "https://www.onyx.security",
        "industry_category": "Secure AI Control Plane",
        "ats_type": None,
        "ats_url": None,
        "job_card_selector": "a[href*='comeet.com'], [class*='job'], div.row",
        "title_selector": "h2, h3, h4, span, a",
        "job_url_selector": "a[href*='comeet.com']",
        "location_selector": "[class*='location'], span"
    },
    {
        "name": "Ema",
        "careers_url": "https://www.ema.co/careers",
        "website": "https://www.ema.co",
        "industry_category": "Enterprise AI Agents",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/ema",
        "job_card_selector": "a[href*='/ema/']",
        "title_selector": "h3, span",
        "job_url_selector": "a[href*='/ema/']",
        "location_selector": "p, [class*='location']"
    },
    {
        "name": "Nscale",
        "careers_url": "https://www.nscale.com/careers",
        "website": "https://www.nscale.com",
        "industry_category": "Full-Stack AI Infrastructure",
        "ats_type": None,
        "ats_url": None,
        "job_card_selector": "[class*='job'], [class*='career'], article, div.row",
        "title_selector": "h2, h3, h4, a",
        "job_url_selector": "a",
        "location_selector": "[class*='location'], span"
    },
    {
        "name": "Wonderful",
        "careers_url": "https://wonderful.ai/",
        "website": "https://wonderful.ai",
        "industry_category": "Enterprise AI Agent Platform",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/wonderful",
        "job_card_selector": "a[href*='/wonderful/']",
        "title_selector": "h3, span",
        "job_url_selector": "a[href*='/wonderful/']",
        "location_selector": "p, [class*='location']"
    },
    {
        "name": "Artisan",
        "careers_url": "https://artisan.co/careers",
        "website": "https://artisan.co",
        "industry_category": "Autonomous AI Employees",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/artisan",
        "job_card_selector": "a[href*='/artisan/']",
        "title_selector": "h3, span",
        "job_url_selector": "a[href*='/artisan/']",
        "location_selector": "p, [class*='location']"
    },
    {
        "name": "Emerald AI",
        "careers_url": "https://www.emeraldai.co/",
        "website": "https://www.emeraldai.co/",
        "industry_category": "Data Center Power Flexibility & Climate AI",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/emerald-ai",
        "job_card_selector": "a[href*='/emerald-ai/']",
        "title_selector": "h3, span",
        "job_url_selector": "a[href*='/emerald-ai/']",
        "location_selector": "p, [class*='location']"
    },
    {
        "name": "Nevis",
        "careers_url": "https://neviswealth.com/",
        "website": "https://neviswealth.com",
        "industry_category": "AI for Wealth Management",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/nevis",
        "job_card_selector": "a[href*='/nevis/']",
        "title_selector": "h3, span",
        "job_url_selector": "a[href*='/nevis/']",
        "location_selector": "p, [class*='location']"
    },
    {
        "name": "Canals",
        "careers_url": "https://canals.ai/",
        "website": "https://canals.ai",
        "industry_category": "AI for Industrial Supply Chains",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/canals",
        "job_card_selector": "a[href*='/canals/']",
        "title_selector": "h3, span",
        "job_url_selector": "a[href*='/canals/']",
        "location_selector": "p, [class*='location']"
    },
    {
        "name": "Triomics",
        "careers_url": "https://www.triomics.com/careers",
        "website": "https://www.triomics.com",
        "industry_category": "Generative AI for Oncology",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/triomics",
        "job_card_selector": "a[href*='/triomics/']",
        "title_selector": "h3, span",
        "job_url_selector": "a[href*='/triomics/']",
        "location_selector": "p, [class*='location']"
    },
    {
        "name": "vLLM",
        "careers_url": "https://vllm.ai/",
        "website": "https://vllm.ai",
        "industry_category": "LLM Inference Engine & Open Source Systems",
        "ats_type": None,
        "ats_url": None,
        "job_card_selector": "[class*='job'], article, a",
        "title_selector": "h2, h3, a",
        "job_url_selector": "a",
        "location_selector": "span"
    },
    {
        "name": "CrewAI",
        "careers_url": "https://www.crewai.com/careers",
        "website": "https://www.crewai.com",
        "industry_category": "Multi-Agent AI Platform",
        "ats_type": "workable",
        "ats_url": "https://apply.workable.com/crewai/",
        "job_card_selector": "[data-ui='job-item'], li, tr",
        "title_selector": "h3, a",
        "job_url_selector": "a",
        "location_selector": "[data-ui='job-location']"
    },
    {
        "name": "PixVerse",
        "careers_url": "https://pixverse.ai/en/careers",
        "website": "https://pixverse.ai",
        "industry_category": "Generative AI Video Platform",
        "ats_type": None,
        "ats_url": None,
        "job_card_selector": "[class*='job'], [class*='career'], article, div",
        "title_selector": "h2, h3, h4, a",
        "job_url_selector": "a",
        "location_selector": "span, p"
    },
    {
        "name": "Ledgebrook",
        "careers_url": "https://www.ledgebrook.com/careers",
        "website": "https://www.ledgebrook.com",
        "industry_category": "AI-Native Specialty Insurance",
        "ats_type": None,
        "ats_url": None,
        "job_card_selector": "a[href*='careerpuck.com'], [class*='job']",
        "title_selector": "h3, h4, span, div",
        "job_url_selector": "a[href*='careerpuck.com']",
        "location_selector": "span, p"
    },
    {
        "name": "Granola",
        "careers_url": "https://www.granola.ai/careers",
        "website": "https://www.granola.ai",
        "industry_category": "AI Meeting Notepad & Workspace",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/granola",
        "job_card_selector": "a[href*='/granola/']",
        "title_selector": "h3, span",
        "job_url_selector": "a[href*='/granola/']",
        "location_selector": "p, [class*='location']"
    },
    {
        "name": "Grammarly",
        "careers_url": "https://www.grammarly.com/careers",
        "website": "https://www.grammarly.com",
        "industry_category": "AI Writing Assistant",
        "ats_type": None,
        "ats_url": None,
        "job_card_selector": "[class*='job'], [class*='card'], article",
        "title_selector": "h2, h3, h4, a",
        "job_url_selector": "a",
        "location_selector": "span, p"
    },
    {
        "name": "Runpod",
        "careers_url": "https://www.runpod.io/careers",
        "website": "https://www.runpod.io",
        "industry_category": "AI Developer Cloud & GPU Infrastructure",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/runpod",
        "job_card_selector": "a[href*='/runpod/']",
        "title_selector": "h3, span",
        "job_url_selector": "a[href*='/runpod/']",
        "location_selector": "p, [class*='location']"
    },
    {
        "name": "TENEX.AI",
        "careers_url": "https://tenex.ai/",
        "website": "https://tenex.ai",
        "industry_category": "AI-Native Managed Detection and Response (MDR)",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/tenex",
        "job_card_selector": "a[href*='/tenex/']",
        "title_selector": "h3, span",
        "job_url_selector": "a[href*='/tenex/']",
        "location_selector": "p, [class*='location']"
    },
    {
        "name": "Novee Security",
        "careers_url": "https://novee.security/careers/",
        "website": "https://novee.security",
        "industry_category": "Autonomous AI Penetration Testing",
        "ats_type": None,
        "ats_url": None,
        "job_card_selector": "[class*='job'], [class*='position'], div.item, a[href*='comeet']",
        "title_selector": "h2, h3, h4, a",
        "job_url_selector": "a",
        "location_selector": "span, p"
    },
    {
        "name": "Seekr",
        "careers_url": "https://www.seekr.com/careers/",
        "website": "https://www.seekr.com",
        "industry_category": "Explainable Enterprise AI Platform",
        "ats_type": None,
        "ats_url": None,
        "job_card_selector": "[class*='job'], [class*='opening'], div.card, article",
        "title_selector": "h2, h3, h4, a",
        "job_url_selector": "a",
        "location_selector": "span, p"
    },
    {
        "name": "Exaforce",
        "careers_url": "https://www.exaforce.com/careers",
        "website": "https://www.exaforce.com",
        "industry_category": "Agentic SOC Platform",
        "ats_type": None,
        "ats_url": None,
        "job_card_selector": "a[href*='/careers/'], [class*='job']",
        "title_selector": "h2, h3, h4, div",
        "job_url_selector": "a[href*='/careers/']",
        "location_selector": "p, span"
    },
    {
        "name": "OpenEvidence",
        "careers_url": "https://www.openevidence.com/",
        "website": "https://www.openevidence.com",
        "industry_category": "AI Copilot for Clinicians & Healthcare",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/openevidence",
        "job_card_selector": "a[href*='/openevidence/']",
        "title_selector": "h3, span",
        "job_url_selector": "a[href*='/openevidence/']",
        "location_selector": "p, [class*='location']"
    },
    {
        "name": "Zafran Security",
        "careers_url": "https://www.zafran.io/careers",
        "website": "https://www.zafran.io",
        "industry_category": "AI Threat Exposure Management",
        "ats_type": "ashby",
        "ats_url": "https://jobs.ashbyhq.com/zafran-security",
        "job_card_selector": "a[href*='/zafran-security/']",
        "title_selector": "h3, span",
        "job_url_selector": "a[href*='/zafran-security/']",
        "location_selector": "p, [class*='location']"
    }
]

def sync_to_sqlite():
    conn = create_connection()
    cursor = conn.cursor()
    
    print(f"[*] Syncing {len(AI_REMOTE_COMPANIES)} AI remote companies to SQLite companies table...")
    added_count = 0
    updated_count = 0
    
    for comp in AI_REMOTE_COMPANIES:
        name = comp["name"]
        careers_url = comp["careers_url"]
        website = comp.get("website", "")
        ats_type = comp.get("ats_type")
        ats_url = comp.get("ats_url")
        job_card = comp.get("job_card_selector", "")
        title_sel = comp.get("title_selector", "")
        url_sel = comp.get("job_url_selector", "")
        loc_sel = comp.get("location_selector", "")
        category = comp.get("industry_category", "AI & Machine Learning")
        
        # Check if company exists by name or careers_url
        cursor.execute("SELECT id, name, careers_url, ats_type, ats_url FROM companies WHERE LOWER(name) = LOWER(?) OR careers_url = ?", (name, careers_url))
        row = cursor.fetchone()
        
        if row:
            comp_id = row[0]
            cursor.execute("""
                UPDATE companies
                SET careers_url = ?, website = ?, ats_type = ?, ats_url = ?,
                    job_card_selector = ?, title_selector = ?, job_url_selector = ?, location_selector = ?,
                    industry_category = ?
                WHERE id = ?
            """, (careers_url, website, ats_type, ats_url, job_card, title_sel, url_sel, loc_sel, category, comp_id))
            updated_count += 1
            print(f"    [UPDATE] {name} (ID: {comp_id}) -> ATS: {ats_type or 'Direct'}")
        else:
            now_iso = datetime.datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO companies (name, careers_url, website, ats_type, ats_url, job_card_selector, title_selector, job_url_selector, location_selector, industry_category, date_added)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, careers_url, website, ats_type, ats_url, job_card, title_sel, url_sel, loc_sel, category, now_iso))
            added_count += 1
            print(f"    [INSERT] {name} -> ATS: {ats_type or 'Direct'}")
            
    conn.commit()
    conn.close()
    print(f"[OK] SQLite sync complete: {added_count} added, {updated_count} updated.")

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
    for comp in AI_REMOTE_COMPANIES:
        name = comp["name"]
        url = comp["careers_url"]
        cat = comp.get("industry_category", "AI & Machine Learning")
        
        entry = {
            "name": name,
            "careers_url": url,
            "category": cat
        }
        
        idx = existing_names.get(name.lower())
        if idx is None and url.lower() in existing_urls:
            idx = existing_urls[url.lower()]
            
        if idx is not None:
            existing_companies[idx]["careers_url"] = url
            existing_companies[idx]["category"] = cat
            updated += 1
        else:
            existing_companies.append(entry)
            added += 1
            
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(existing_companies, f, indent=2)
    print(f"[OK] Synced base_companies.json: {added} new entries added, {updated} updated.")

def main():
    print("=== TalentScout: Ingesting Subhankar Halder's 30 AI Remote-First Companies ===")
    sync_to_sqlite()
    sync_base_companies_json()
    print("\n[SUCCESS] All 30 AI remote-first companies successfully configured for auto_scour.py!")

if __name__ == "__main__":
    main()
