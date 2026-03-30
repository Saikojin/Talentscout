import asyncio
import datetime
import json
import os
import re
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
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Warning: {filepath} not found.")
    return {}

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

async def scrape_company(context, company, semaphore):
    name = company["name"]
    url = company["careers_url"]
    
    async with semaphore:
        page = await context.new_page()
        print(f"\n[*] Scraping Company: {name}...")
        
        print(f"[*] Navigating to {url}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
    except Exception as e:
        print(f"[!] Warning: Navigation to {url} timed out or failed. {e}")
        
    card_sel = company.get("job_card_selector")
    
    jobs = []
    
    if not card_sel:
        # Smart Callback: No selectors defined in DB. We will heuristically find job links.
        print(f"[*] No selectors defined for {name}. Using smart fallback to find job links...")
        
        # Pull all links from the DOM instantly to avoid timeout issues
        try:
            links_data = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll("a")).map(a => ({
                    href: a.getAttribute("href") || a.href || "",
                    text: a.innerText || ""
                }));
            }''')
        except Exception as e:
            print(f"      [!] Error extracting links: {e}")
            links_data = []
            
        for data in links_data:
            href = data.get("href", "")
            text = data.get("text", "")
            if href and text and text.strip():
                href_lower = href.lower()
                # Check for common job URL patterns or exact roles
                keywords = ["/job", "/career", "/req", "/position", "jobid=", "opening", "opportunity", "role"]
                if any(k in href_lower for k in keywords):
                    # Exclude generic nav links
                    if "search" not in href_lower and "login" not in href_lower and "mailto:" not in href_lower:
                        full_url = href if href.startswith('http') else urljoin(url, href)
                        jobs.append({
                            "title": text.strip(),
                            "company": name,
                            "url": full_url
                        })
        
        # Deduplicate discovered jobs
        unique_jobs = {}
        for j in jobs:
            # Prefer shorter URLs (avoids tracking params if they differ)
            if j["url"] not in unique_jobs:
                unique_jobs[j["url"]] = j
        
        jobs = list(unique_jobs.values())
        print(f"[*] Smart fallback found {len(jobs)} potential job links.")
        await page.close()
        return jobs[:30]
        
    try:
        await page.wait_for_selector(card_sel, timeout=10000)
    except Exception:
        log(f"[!] Could not find any job cards ('{card_sel}') on this page.")
        return []

    cards = await page.locator(card_sel).all()
    log(f"[*] Found {len(cards)} job postings for {name}. Analyzing...")
    
    # Process up to 30 like job boards
    for idx, card in enumerate(cards[:30]):
        log(f"    - Processing card {idx+1}/{min(len(cards), 30)}...")
        try:
            # Check for old dates in card text early to skip unnecessary processing
            card_text = await card.text_content()
            if card_text:
                clower = card_text.lower()
                old_phrases = ["30+ days", "30 days", "month ago", "months ago", "60 days", "90 days"]
                if any(p in clower for p in old_phrases):
                    log(f"  [-] Skipping old job (found date text in card)")
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
    
    await page.close()
    return jobs

async def scrape_site(context, site_name, site_info, config, search_term, location, semaphore):
    async with semaphore:
        page = await context.new_page()
        log(f"  [*] Starting: {site_name} ('{search_term}' in '{location}')")
    
        search_url_pattern = config.get("search_url")
        if not search_url_pattern: 
            log(f"[!] No search_url pattern for {site_name}")
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
        log(f"[*] Found {len(cards)} job cards. Analyzing...")
        
        if "linkedin.com" in url and "login" in page.url.lower():
            log("[!] LinkedIn redirect to login detected! Scraping may fail.")
            return []
        
        jobs = []
        # Only process up to 30 to save time during testing
        for idx, card in enumerate(cards[:30]):
            log(f"    - Processing card {idx+1}/{min(len(cards), 30)}...")
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
                
        await page.close()
        print(f"  [+] Finished: {site_name} ('{search_term}' in '{location}'). Found {len(jobs)} jobs.")
        return jobs

async def fetch_job_description(context, job_url, semaphore):
    async with semaphore:
        page = await context.new_page()
        description = ""
        try:
            print(f"  [-] Fetching JD from {job_url}")
            await page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
            description = await page.evaluate("document.body.innerText")
        except Exception as e:
            print(f"  [!] Failed to load JD: {e}")
        finally:
            await page.close()
    return description

MAX_CONCURRENT_PAGES = 5

async def discover_jobs_from_config(context, config, semaphore, blacklist):
    site_name = config["site_name"]
    
    # Check blacklist
    is_blacklisted = False
    for blocked in blacklist:
        if blocked.lower() in site_name.lower() or (config.get("url") and blocked.lower() in config.get("url").lower()):
            is_blacklisted = True
            break
    
    if is_blacklisted:
        print(f"[*] Skipping blacklisted site: {site_name}")
        return []

    search_terms = config.get("search_terms") or ["Senior QA Engineer"]
    locations = config.get("locations") or ["Seattle"]
    
    all_discovered = []
    for search_term in search_terms:
        for location in locations:
            jobs = await scrape_site(context, site_name, config, config, search_term, location, semaphore)
            for job in jobs:
                job["site"] = site_name
            all_discovered.extend(jobs)
    return all_discovered

async def discover_jobs_from_company(context, company, semaphore):
    site_name = company["name"]
    jobs = await scrape_company(context, company, semaphore)
    for job in jobs:
        job["site"] = site_name
    return jobs

async def process_discovered_job(context, job, semaphore, processed_urls):
    if not job["url"] or job["url"] in processed_urls:
        return None
        
    processed_urls.add(job["url"])
    
    if is_duplicate(job["url"], job["title"], job["company"]):
        print(f"  [-] Skipping existing job: {job['title']} at {job['company']}")
        return None
        
    try:
        jd_text = await asyncio.wait_for(fetch_job_description(context, job["url"], semaphore), timeout=45)
    except asyncio.TimeoutError:
        print(f"  [!] Timeout fetching JD for {job['url']}")
        return None
    
    filter_results = filter_job(jd_text, SKILLSET_FILE)
    job["filter_results"] = filter_results
    
    if filter_results.get("is_disqualified"):
        print(f"  [-] Job Disqualified: {job['title']} at {job['company']}")
        return job # Return anyway to show in final "failed" list if needed
        
    score = filter_results.get("score", 75)
    missing_skills = filter_results.get("missing_skills", [])[:3]
    matched_skills = filter_results.get("matched_skills", [])[:5] 
    
    add_job(job["title"], job["company"], job["url"], job["site"], score, missing_skills, matched_skills)
    return job

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
        
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAGES)
        processed_urls = set()
        
        # 1. DISCOVERY PHASE (Parallel)
        log("\n=== Phase 1: Discovering Jobs ===")
        discovery_tasks = []
        for config in search_configs:
            # Wrap each site discovery in a timeout (5 mins) to prevent total hang
            task = asyncio.wait_for(discover_jobs_from_config(context, config, semaphore, blacklist), timeout=300)
            discovery_tasks.append(task)
        for company in companies:
            task = asyncio.wait_for(discover_jobs_from_company(context, company, semaphore), timeout=120)
            discovery_tasks.append(task)
            
        # Use return_exceptions=True so one failure doesn't kill the whole run
        discovery_results_raw = await asyncio.gather(*discovery_tasks, return_exceptions=True)
        
        discovery_results = []
        for i, res in enumerate(discovery_results_raw):
            if isinstance(res, Exception):
                log(f"[!] Phase 1 Task {i} failed with error: {res}")
            else:
                discovery_results.append(res)
        
        # Flatten results
        all_discovered = [job for sublist in discovery_results for job in sublist]
        log(f"\n[*] Discovery complete. Found {len(all_discovered)} potential jobs.")
        
        # 2. PROCESSING PHASE (Parallel)
        log("\n=== Phase 2: Fetching Descriptions and Filtering ===")
        processing_tasks = []
        # Wrap each processing task with a timeout just in case
        log(f"[*] Processing {len(all_discovered)} jobs...")
        for i, job in enumerate(all_discovered):
            if i > 0 and i % 10 == 0:
                log(f"    - Progress: {i}/{len(all_discovered)} jobs submitted...")
            processing_tasks.append(process_discovered_job(context, job, semaphore, processed_urls))
            
        processed_results = await asyncio.gather(*processing_tasks)
        all_results = [r for r in processed_results if r is not None]
        
        await browser.close()
        
        # Filter down to actually added jobs for the summary
        successful_jobs = [j for j in all_results if not j.get("filter_results", {}).get("is_disqualified")]
        
        # Print summary
        log("\n=== Scour Summary ===")
        log(f"Total Discovered: {len(all_discovered)}")
        log(f"Total Processed (Unique): {len(all_results)}")
        log(f"Jobs Added/Passed: {len(successful_jobs)}")
        
        # Save to a temp log file
        with open("logs/auto_scour_results.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)
        log("\n[*] Results saved to logs/auto_scour_results.json")
        
        # Update Markdown
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
        
        if os.path.exists("jobs_to_review.md"):
            with open("jobs_to_review.md", "r", encoding="utf-8") as f:
                md_content = f.read()
                
            if md_updates_passed or md_updates_failed:
                split_md = md_content.split("## Disqualified Jobs")
                table_part = split_md[0].rstrip()
                disq_part = split_md[1] if len(split_md) > 1 else ""
                
                if md_updates_passed:
                    # Deduplicate: only add if the same URL isn't already in the file
                    for line in md_updates_passed:
                        # Simple check for the URL or Title/Company in the existing content
                        # Since it's a markdown table, the URL is in [Apply](URL)
                        # We extract the URL from the new line
                        job_url_match = re.search(r'\[Apply\]\((.*?)\)', line)
                        if job_url_match:
                            job_url = job_url_match.group(1)
                            if job_url not in table_part:
                                table_part += "\n" + line
                
                new_md = table_part + "\n\n## Disqualified Jobs"
                
                if md_updates_failed:
                    # Append unique failed jobs
                    for line in md_updates_failed:
                        if line not in disq_part:
                            disq_part += "\n" + line
                
                new_md += disq_part
                
                with open("jobs_to_review.md", "w", encoding="utf-8") as f:
                    f.write(new_md)
            log(f"[*] Updated jobs_to_review.md")



if __name__ == "__main__":
    asyncio.run(main())
