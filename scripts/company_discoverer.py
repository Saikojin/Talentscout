import asyncio
import os
import sys
import re
from urllib.parse import urlparse, quote_plus, parse_qs
from collections import Counter
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Ensure imports work regardless of run location
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.database import company_exists_by_domain, add_company
from scripts.crawler_learner import extract_domain, get_class_selector, interactive_selection

IGNORED_DOMAINS = [
    "duckduckgo.com", "google.com", "bing.com", "yahoo.com",
    "facebook.com", "twitter.com", "instagram.com", "youtube.com", "tiktok.com",
    "apple.com", "amazon.com", "wikipedia.org", "en.wikipedia.org",
    "linkedin.com", "indeed.com", "glassdoor.com", "builtin.com", 
    "ziprecruiter.com", "monster.com", "simplyhired.com", "careerbuilder.com",
    "ycombinator.com", "levels.fyi", "reddit.com", "medium.com"
]

def format_company_name(domain):
    parts = domain.split('.')
    if len(parts) > 1:
        return parts[-2].capitalize()
    return domain.capitalize()

def extract_real_url(href):
    if not href:
        return None
    if href.startswith('//duckduckgo.com/l/'):
        parsed = parse_qs(urlparse(href).query)
        if 'uddg' in parsed:
            return parsed['uddg'][0]
    return href if href.startswith('http') else None

async def extract_links_from_page(page, url):
    print(f"\n[*] Scanning '{url}' for company links...")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        await page.wait_for_timeout(3000)
        # Scroll down to load more
        await page.mouse.wheel(0, 3000)
        await page.wait_for_timeout(2000)
        
        c_html = await page.content()
        soup = BeautifulSoup(c_html, 'html.parser')
        
        discovered_targets = []
        seen_domains = set()
        
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href')
            if href.startswith('http'):
                domain = extract_domain(href)
                base_domain = '.'.join(domain.split('.')[-2:]) if domain.count('.') > 0 else domain
                
                # Filter out obvious non-companies
                if any(ignored in domain for ignored in IGNORED_DOMAINS) or base_domain in seen_domains:
                    continue
                    
                if not company_exists_by_domain(base_domain):
                    cname = format_company_name(base_domain)
                    seen_domains.add(base_domain)
                    discovered_targets.append({
                        "name": cname,
                        "url": href,
                        "domain": base_domain
                    })
                    
        return discovered_targets
    except Exception as e:
        print(f"[!] Warning: Failed to scan {url}: {e}")
        return []

async def discover_companies(search_term):
    print(f"\n[*] Searching DuckDuckGo for: '{search_term}'...")
    
    url = f"https://duckduckgo.com/?q={quote_plus(search_term)}"
    
    async with async_playwright() as p:
        # Give the user visual feedback and solve captchas if duckduckgo suspects bot
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 1080}
        )
        page = await context.new_page()
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=40000)
            print("[*] Retrieving organic results... (Solve captcha if prompted)")
            # Wait a bit for results to render
            await page.wait_for_timeout(3000)
        except Exception as e:
            print(f"[!] Target search failed: {e}")
            await browser.close()
            return

        html_content = await page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        search_results = []
        
        # DuckDuckGo's standard DOM usually wraps organic results in 'article'
        articles = soup.find_all('article')
        for art in articles:
            # The main link is typically an anchor inside an h2 or similar heading
            title_el = art.find('a', {'data-testid': 'result-title-a'}) 
            if not title_el:
                title_el = art.find('h2')
                if title_el: title_el = title_el.find('a')
                
            if title_el:
                href = extract_real_url(title_el.get('href'))
                title_text = title_el.text.strip()
                
                if href and extract_domain(href) not in IGNORED_DOMAINS:
                    search_results.append({
                        "title": title_text,
                        "url": href,
                        "domain": extract_domain(href)
                    })

        if not search_results:
            print("[!] No results found. Trying alternative method...")
            links = soup.find_all('a', href=True)
            for link in links:
                href = extract_real_url(link.get('href'))
                if href and extract_domain(href) not in IGNORED_DOMAINS:
                    search_results.append({
                        "title": link.text.strip() or href,
                        "url": href,
                        "domain": extract_domain(href)
                    })
        
        print(f"\n[*] Found {len(search_results)} search results.")
        for idx, res in enumerate(search_results[:15]):
            print(f"  [{idx+1}] {res['title'][:60]} ({res['domain']})")
            
        print("\nYou can either:")
        print(" [number] Scan an article/list above to discover companies inside it.")
        print(" [0]      Process these search results directly as companies.")
        print(" [q]      Quit.")
        
        choice = input("\nEnter your choice: ").strip()
        if choice.lower() == 'q':
            await browser.close()
            return
            
        urls_to_visit = []
        
        try:
            choice_idx = int(choice)
            if choice_idx > 0 and choice_idx <= len(search_results):
                target_result = search_results[choice_idx-1]
                print(f"[*] Chosen to recursively scan: {target_result['title']}")
                urls_to_visit = await extract_links_from_page(page, target_result['url'])
                print(f"[*] Extracted {len(urls_to_visit)} potential companies from the article.")
            else:
                print("[*] Processing search results directly as companies...")
                for res in search_results:
                    domain = res['domain']
                    base_domain = '.'.join(domain.split('.')[-2:]) if domain.count('.') > 0 else domain
                    if any(ignored in domain for ignored in IGNORED_DOMAINS):
                        continue
                    if not company_exists_by_domain(base_domain):
                        urls_to_visit.append({
                            "name": format_company_name(base_domain),
                            "url": res['url'],
                            "domain": base_domain
                        })
        except ValueError:
            print("[!] Invalid input. Exiting.")
            await browser.close()
            return

        if not urls_to_visit:
            print("[*] No new companies found to process. They might all be known, or list is empty.")
            await browser.close()
            return
            
        print(f"\n[*] Beginning Interactive Discovery for {len(urls_to_visit)} companies...")
        
        for idx, target in enumerate(urls_to_visit):
            cname = target['name']
            curl = target['url']
            
            print(f"\n=============================================")
            print(f"[{idx+1}/{len(urls_to_visit)}] Analyzing Company: {cname}")
            print(f"URL: {curl}")
            print(f"=============================================")
            
            ans = input(f"Do you want to process '{cname}'? (y/n/skip): ").strip().lower()
            if ans != 'y':
                continue
                
            try:
                print(f"[*] Loading page and waiting for network idle...")
                # To discover career pages, sometimes we need to navigate specifically to /careers
                if '/careers' not in curl and '/jobs' not in curl:
                    print(f"  [-] Note: the URL '{curl}' might just be the homepage.")
                    go_careers = input(f"  [-] Try appending '/careers' to it? (y/n): ").strip().lower()
                    if go_careers == 'y':
                        if curl.endswith('/'):
                            curl += "careers"
                        else:
                            curl += "/careers"
                            
                await page.goto(curl, wait_until="networkidle", timeout=40000)
                await page.wait_for_timeout(3000)
                
                # Scroll to load lazy elements
                await page.mouse.wheel(0, 2000)
                await page.wait_for_timeout(2000)
                
                c_html = await page.content()
                c_soup = BeautifulSoup(c_html, 'html.parser')
                
                # Similar heuristics to crawler_learner.py
                divs = c_soup.find_all(['div', 'li'])
                div_classes = [get_class_selector(d) for d in divs if get_class_selector(d)]
                container_candidates = [(cls, count) for cls, count in Counter(div_classes).most_common(15) if count > 3]
                
                headers = c_soup.find_all(['h2', 'h3', 'h4'])
                header_classes = [get_class_selector(h) for h in headers if get_class_selector(h)]
                title_candidates = [(cls, count) for cls, count in Counter(header_classes).most_common(10)]
                
                links = c_soup.find_all('a', href=True)
                link_classes = [get_class_selector(a) for a in links if get_class_selector(a)]
                url_candidates = [(cls, count) for cls, count in Counter(link_classes).most_common(15) if count > 3]
                
                print("\n*** Visual Selector Configuration ***")
                card_sel = await interactive_selection(page, container_candidates, "Job Card Container", "red")
                if not card_sel:
                    print("Skipping company (no card selector provided).")
                    continue
                    
                title_sel = await interactive_selection(page, title_candidates, "Job Title", "blue")
                url_sel = await interactive_selection(page, url_candidates, "Job URL", "green")
                
                company_sel = input(f"\n[Optional] Enter company selector (default applies '{cname}' statically): ").strip()
                
                print(f"\n[*] Saving company config for {cname}...")
                cid = add_company(cname, curl, card_sel, title_sel, company_sel, url_sel)
                if cid:
                    print(f"  [+] Saved {cname} successfully to database (ID: {cid})")
                
            except Exception as e:
                print(f"[!] Error processing {cname}: {e}")
                
        await browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/company_discoverer.py \"<search query>\"")
        print("Example: python scripts/company_discoverer.py \"seattle software technology companies careers page\"")
        sys.exit(1)
        
    query = " ".join(sys.argv[1:])
    asyncio.run(discover_companies(query))
