import asyncio
import json
import os
import sys
from urllib.parse import urljoin
from playwright.async_api import async_playwright

# Append current dir to sys.path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from scripts.filter_skills import filter_job
    from scripts.database import is_duplicate, add_job, get_all_search_configs, get_all_companies
    from scripts.cleanup import clean_logs
except ImportError:
    print("Error: Could not import local modules. Make sure you are running from the project root.")
    sys.exit(1)

CONFIG_FILE = "site_selectors.json" #"site_configs.json"
SITES_FILE = "job_search_sites.json"
SKILLSET_FILE = "base_skillset.json"
BLACKLIST_FILE = "blacklist.json"

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    print(f"Warning: {filepath} not found.")
    return {}

async def scrape_company(page, company):
    name = company["name"]
    url = company["careers_url"]
    print(f"\n[*] Scraping Company: {name}...")
    
    print(f"[*] Navigating to {url}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
    except Exception as e:
        print(f"[!] Warning: Navigation to {url} timed out or failed. {e}")
        
    card_sel = company.get("job_card_selector")
    if not card_sel: return []
    
    try:
        await page.wait_for_selector(card_sel, timeout=10000)
    except Exception:
        print(f"[!] Could not find any job cards ('{card_sel}') on this page.")
        return []

    cards = await page.locator(card_sel).all()
    print(f"[*] Found {len(cards)} job postings for {name}. Analyzing...")
    
    jobs = []
    # Process up to 30 like job boards
    for idx, card in enumerate(cards[:30]):
        try:
            # Check for old dates in card text early to skip unnecessary processing
            card_text = await card.text_content()
            if card_text:
                clower = card_text.lower()
                old_phrases = ["30+ days", "30 days", "month ago", "months ago", "60 days", "90 days"]
                if any(p in clower for p in old_phrases):
                    print(f"  [-] Skipping old job (found date text in card)")
                    continue

            title_el = card.locator(company.get("title_selector")).first
            title = await title_el.text_content() if await title_el.count() else "Unknown Title"
            
            c_sel = company.get("company_selector")
            if c_sel and await card.locator(c_sel).count():
                company_text = await card.locator(c_sel).first.text_content()
            else:
                company_text = name # fallback to known company name
                
            job_href = None
            url_el = card.locator(company.get("job_url_selector") or "a").first
            if await url_el.count():
                job_href = await url_el.get_attribute("href")
            
            if not job_href:
                links = await card.locator("a").all()
                for link in links:
                    href = await link.get_attribute("href")
                    if href:
                        job_href = href
                        break
                        
            if job_href and not job_href.startswith('http'):
                job_href = urljoin(url, job_href)
                
            jobs.append({
                "title": title.strip(),
                "company": company_text.strip(),
                "url": job_href or url
            })
        except Exception as e:
            continue

    return jobs

async def scrape_site(page, site_name, site_info, config, search_term, location):
    print(f"\n[*] Scraping {site_name} with '{search_term}' in '{location}'...")
    
    search_url_pattern = config.get("search_url")
    if not search_url_pattern: 
        print(f"[!] No search_url pattern for {site_name}")
        return []
        
    url = search_url_pattern.replace("{search_term}", search_term.replace(" ", "%20"))
    url = url.replace("{location}", location.replace(" ", "%20"))

    print(f"[*] Navigating to {url}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        # Some sites need a bit more time for AJAX cards
        await asyncio.sleep(2)
    except Exception as e:
        print(f"[!] Warning: Navigation to {url} timed out or failed. {e}")
        
    # Wait for job cards to load
    card_sel = config.get("job_card_selector")
    try:
        await page.wait_for_selector(card_sel, timeout=10000)
    except Exception:
        print(f"[!] Could not find any job cards ('{card_sel}') on this page.")
        return []

    cards = await page.locator(card_sel).all()
    print(f"[*] Found {len(cards)} job cards. Analyzing the top 3...")
    
    jobs = []
    # Only process up to 30 to save time during testing
    for idx, card in enumerate(cards[:30]):
        try:
            # Check for old dates in card text early to skip unnecessary processing
            card_text = await card.text_content()
            if card_text:
                clower = card_text.lower()
                old_phrases = ["30+ days", "30 days", "month ago", "months ago", "60 days", "90 days"]
                if any(p in clower for p in old_phrases):
                    continue

            # Extract basic info
            title_el = card.locator(config.get("title_selector")).first
            company_el = card.locator(config.get("company_selector")).first
            
            title = await title_el.text_content() if await title_el.count() else "Unknown Title"
            company = await company_el.text_content() if await company_el.count() else "Unknown Company"
            
            # Extract all links from the card to find the right one
            job_href = None
            links = await card.locator("a").all()
            for link in links:
                href = await link.get_attribute("href")
                if href and ("/job/" in href or "/post/" in href):
                    job_href = href
                    break
            
            if not job_href:
                url_el = card.locator(config.get("job_url_selector")).first
                job_href = await url_el.get_attribute("href") if await url_el.count() else None
            
            title = title.strip()
            # Clean up company name if it's missing or has extra whitespace
            if company and company.strip() and company.strip() != "Unknown Company":
                company = company.strip()
            else:
                # Fallback: Many sites use a sibling <span> or a <div> just below the title
                try:
                    all_text_elements = await card.locator("span").all_text_contents()
                    for t in all_text_elements:
                        if t and len(t.strip()) > 3 and "Apply" not in t and "ago" not in t:
                            company = t.strip()
                            break
                except:
                    pass
            
            # Resolve relative URLs
            if job_href and not job_href.startswith('http'):
                job_href = urljoin(url, job_href)
                
            jobs.append({
                "title": title,
                "company": company,
                "url": job_href or url
            })
        except Exception as e:
            print(f"[!] Error parsing card {idx}: {e}")
            continue

    return jobs

async def fetch_job_description(context, job_url):
    print(f"  [-] Fetching JD from {job_url}")
    page = await context.new_page()
    description = ""
    try:
        await page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
        description = await page.evaluate("document.body.innerText")
    except Exception as e:
        print(f"  [!] Failed to load JD: {e}")
    finally:
        await page.close()
    return description

async def main():
    search_configs = get_all_search_configs()
    companies = get_all_companies()
    blacklist = load_json(BLACKLIST_FILE)
    if not isinstance(blacklist, list):
        blacklist = []
    
    if not search_configs and not companies:
        print("[!] No search configurations or companies found in the database. Please add some first.")
        return
        
    # Clean logs before scraping
    clean_logs("logs")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        all_results = []
        
        # 1. Scrape Job Board Search Configs
        processed_urls = set()
        for config in search_configs:
            site_name = config["site_name"]
            
            # Check blacklist
            is_blacklisted = False
            for blocked in blacklist:
                if blocked.lower() in site_name.lower() or (config.get("url") and blocked.lower() in config.get("url").lower()):
                    is_blacklisted = True
                    break
            
            if is_blacklisted:
                print(f"[*] Skipping blacklisted site: {site_name}")
                continue

            search_terms = config.get("search_terms") or ["Senior QA Engineer"]
            locations = config.get("locations") or ["Seattle"]
            
            for search_term in search_terms:
                for location in locations:
                    jobs = await scrape_site(page, site_name, config, config, search_term, location)
                    
                    new_jobs = []
                    for job in jobs:
                        job["site"] = site_name
                        if not job["url"] or job["url"] in processed_urls:
                            continue
                            
                        processed_urls.add(job["url"])
                        
                        if is_duplicate(job["url"], job["title"], job["company"]):
                            print(f"  [-] Skipping existing job: {job['title']} at {job['company']}")
                            continue
                            
                        jd_text = await fetch_job_description(context, job["url"])
                        filter_results = filter_job(jd_text, SKILLSET_FILE)
                        job["filter_results"] = filter_results
                        
                        score = filter_results.get("score", 75)
                        missing_skills = filter_results.get("missing_skills", [])[:3]
                        matched_skills = filter_results.get("matched_skills", [])[:5] 
                        
                        add_job(job["title"], job["company"], job["url"], site_name, score, missing_skills, matched_skills)
                        new_jobs.append(job)
                            
                    all_results.extend(new_jobs)
            
        # 2. Scrape Direct Company Sites
        for company in companies:
            site_name = company["name"]
            jobs = await scrape_company(page, company)
            
            new_jobs = []
            for job in jobs:
                job["site"] = site_name
                if not job["url"] or job["url"] in processed_urls:
                    continue
                    
                processed_urls.add(job["url"])
                
                if is_duplicate(job["url"], job["title"], job["company"]):
                    print(f"  [-] Skipping existing job: {job['title']} at {job['company']}")
                    continue
                    
                jd_text = await fetch_job_description(context, job["url"])
                filter_results = filter_job(jd_text, SKILLSET_FILE)
                job["filter_results"] = filter_results
                
                score = filter_results.get("score", 75)
                missing_skills = filter_results.get("missing_skills", [])[:3]
                matched_skills = filter_results.get("matched_skills", [])[:5] 
                
                add_job(job["title"], job["company"], job["url"], site_name, score, missing_skills, matched_skills)
                new_jobs.append(job)
                    
            all_results.extend(new_jobs)
                
        await browser.close()
        
        # Print summary
        print("\n=== Scour Summary ===")
        print(json.dumps(all_results, indent=2))
        
        # Save to a temp log file for the user to review
        with open("logs/auto_scour_results.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)
        print("\n[*] Results saved to logs/auto_scour_results.json")
        
        # Integrate with tracking files
        md_updates_passed = []
        md_updates_failed = []
        
        for job in all_results:
            fr = job.get("filter_results", {})
            if fr.get("is_disqualified"):
                reason = "/".join(fr.get("disqualified_by", ["Unknown"]))
                md_updates_failed.append(f"- {job['title']} ({job['company']}) - **{reason}**")
            else:
                score = fr.get("score", 75)
                title = job['title']
                company = job['company']
                url = job['url']
                missing_str = ", ".join(fr.get("missing_skills", [])[:3]) if fr.get("missing_skills") else "None"
                
                md_updates_passed.append(f"| {score} | {title} | {company} | AutoScour | {missing_str} | [Apply]({url}) |")
        
        # Update Markdown
        if os.path.exists("jobs_to_review.md"):
            with open("jobs_to_review.md", "r", encoding="utf-8") as f:
                md_content = f.read()
                
            if md_updates_passed:
                # Find the end of the table
                split_md = md_content.split("## Disqualified Jobs")
                table_part = split_md[0].rstrip()
                disq_part = split_md[1] if len(split_md) > 1 else ""
                
                new_table = table_part + "\n" + "\n".join(md_updates_passed) + "\n\n## Disqualified Jobs" + disq_part
                md_content = new_table
                
            if md_updates_failed:
                md_content = md_content.rstrip() + "\n" + "\n".join(md_updates_failed) + "\n"
                
            with open("jobs_to_review.md", "w", encoding="utf-8") as f:
                f.write(md_content)
            print(f"[*] Appended {len(md_updates_passed)} passing and {len(md_updates_failed)} failing jobs to jobs_to_review.md")



if __name__ == "__main__":
    asyncio.run(main())
