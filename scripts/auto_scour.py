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
    from scripts.database import is_duplicate, add_job
    from scripts.cleanup import clean_logs
except ImportError:
    print("Error: Could not import local modules. Make sure you are running from the project root.")
    sys.exit(1)

CONFIG_FILE = "site_selectors.json" #"site_configs.json"
SITES_FILE = "job_search_sites.json"
SKILLSET_FILE = "base_skillset.json"

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    print(f"Warning: {filepath} not found.")
    return {}

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
        # Try to extract text. If there's a specific JD selector we could use it, 
        # but body text is usually good enough for keyword filtering.
        description = await page.evaluate("document.body.innerText")
    except Exception as e:
        print(f"  [!] Failed to load JD: {e}")
    finally:
        await page.close()
    return description

async def main():
    configs = load_json(CONFIG_FILE)
    sites_data = load_json(SITES_FILE)
    
    if not configs:
        print("[!] No site configurations found in site_configs.json. Run crawler_learner.py first.")
        return
        
    sites_to_search = sites_data.get("job_search_sites", [])
    
    # Clean logs before scraping
    clean_logs("logs")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        all_results = []
        
        for site in sites_to_search:
            site_name = site["name"]
            
            # Match by name or fuzzy match
            config = None
            matched_key = None
            for k, v in configs.items():
                if k.lower() in site_name.lower() or site_name.lower() in k.lower():
                    config = v
                    matched_key = k
                    break
                        
            if config:
                search_term = site.get("search_terms", ["Senior QA Engineer"])[0]
                location = site.get("locations", ["Seattle"])[0]
                
                jobs = await scrape_site(page, matched_key, site, config, search_term, location)
                
                # Fetch Descriptions and Filter
                new_jobs = []
                for job in jobs:
                    job["site"] = matched_key # Use the config name as site source
                    if not job["url"]:
                        continue
                        
                    if is_duplicate(job["url"]):
                        print(f"  [-] Skipping existing job: {job['title']} at {job['company']}")
                        continue
                        
                    jd_text = await fetch_job_description(context, job["url"])
                    filter_results = filter_job(jd_text, SKILLSET_FILE)
                    job["filter_results"] = filter_results
                    add_job(job["title"], job["company"], job["url"], matched_key)
                    new_jobs.append(job)
                        
                all_results.extend(new_jobs)
            else:
                print(f"[!] No config found for {site_name}, skipping.")
                
        await browser.close()
        
        # Print summary
        print("\n=== Scour Summary ===")
        print(json.dumps(all_results, indent=2))
        
        # Save to a temp log file for the user to review
        with open("logs/auto_scour_results.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)
        print("\n[*] Results saved to logs/auto_scour_results.json")
        
        # Integrate with tracking files
        dashboard_updates = []
        md_updates_passed = []
        md_updates_failed = []
        
        for job in all_results:
            fr = job.get("filter_results", {})
            if fr.get("is_disqualified"):
                reason = "/".join(fr.get("disqualified_by", ["Unknown"]))
                md_updates_failed.append(f"- {job['title']} ({job['company']}) - **{reason}**")
            else:
                score = 75 # arbitrary default score for new pulls
                title = job['title']
                company = job['company']
                url = job['url']
                missing_str = ", ".join(fr.get("missing_skills", [])[:3]) if fr.get("missing_skills") else "None"
                missing_arr_str = json.dumps(fr.get("missing_skills", [])[:3]) if fr.get("missing_skills") else "[]"
                
                md_updates_passed.append(f"| {score} | {title} | {company} | AutoScour | {missing_str} | [Apply]({url}) |")
                # Safe serialization for JS
                job_obj = {
                    "score": score,
                    "title": title.strip(),
                    "company": company.strip(),
                    "site": job.get("site", "AutoScour"),
                    "missing": fr.get("missing_skills", [])[:3],
                    "url": url
                }
                dashboard_updates.append(f"            {json.dumps(job_obj)}")
        
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
            
        # Update HTML
        if os.path.exists("dashboard.html") and dashboard_updates:
            with open("dashboard.html", "r", encoding="utf-8") as f:
                html_content = f.read()
                
            # Find the jobs array
            import re
            match = re.search(r'(const jobs = \[\n)([\s\S]*?)(\n        \];)', html_content)
            if match:
                prefix = match.group(1)
                suffix = match.group(3)
                
                # Deduplicate based on URL
                seen_urls = set()
                unique_updates = []
                for update in dashboard_updates:
                    url_match = re.search(r'"url": "(.*?)"', update)
                    if url_match:
                        url = url_match.group(1)
                        if url not in seen_urls:
                            seen_urls.add(url)
                            unique_updates.append(update)
                
                new_jobs_str = ",\n".join(unique_updates)
                new_html = html_content[:match.start()] + prefix + new_jobs_str + suffix + html_content[match.end():]
                
                with open("dashboard.html", "w", encoding="utf-8") as f:
                    f.write(new_html)
                print(f"[*] Updated dashboard.html with {len(unique_updates)} unique new jobs (replaced old entries)")



if __name__ == "__main__":
    asyncio.run(main())
