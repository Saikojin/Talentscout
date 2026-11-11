import argparse
import asyncio
import datetime
import json
import os
import re
import socket
import sys
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright

# Append current dir to sys.path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from scripts.filter_skills import filter_job
    from scripts.scorer import score_job
    from scripts.profile import get_active_profile, seed_default_profile
    from scripts.database import is_duplicate, add_job, get_all_search_configs, get_all_companies
    from scripts.cleanup import clean_logs
    from scripts.scour_telemetry import ScourTelemetry, detect_http_block, detect_dom_challenge
    from scripts.pagination_utils import extract_page_count, build_page_url
    from scripts.browser_stealth import create_stealth_context, resolve_transient_challenge
    from scripts.rate_limiter import DomainThrottle, normalize_domain
    from scripts.selector_heuristics import (
        find_fallback_cards,
        extract_fallback_title,
        extract_fallback_link,
        extract_fallback_company,
        extract_fallback_location,
        is_likely_job_url,
    )
except ImportError:
    print("Error: Could not import local modules. Make sure you are running from the project root.")
    sys.exit(1)

CONFIG_FILE = "site_selectors.json"
SITES_FILE = "job_search_sites.json"
SKILLSET_FILE = "base_skillset.json"
BLACKLIST_FILE = "blacklist.json"

def parse_args(args=None):
    """Parse CLI options for pagination, page skipping, telemetry, and dry runs."""
    parser = argparse.ArgumentParser(description="TalentScout Automated Job Scraper")
    parser.add_argument("--page", type=int, default=1, help="Target search results page to scrape (default: 1)")
    parser.add_argument("--skip-page-one", action="store_true", help="Ignore page 1 results and scour starting from page 2 (or specified --page)")
    parser.add_argument("--max-pages", type=int, default=1, help="Max number of pages to scour per site (default: 1)")
    parser.add_argument("--detect-pages-only", action="store_true", help="Probe sites to detect available pages and bot blocks without extracting/scoring JDs")
    parser.add_argument("--dry-run", action="store_true", help="Simulate scour and scoring without saving to DB or updating jobs_to_review.md")
    return parser.parse_args(args)

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Warning: {filepath} not found.")
    return {}

def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")

_DNS_CACHE = {}

def is_blacklisted(url: str, name: str, blacklist_set: set) -> bool:
    """Fast check against the blacklist set for domain, hostname, parent domain, or name."""
    if not blacklist_set:
        return False
    if url:
        hostname = urlparse(url).netloc.lower().strip()
        if hostname:
            if hostname in blacklist_set:
                return True
            if hostname.startswith("www.") and hostname[4:] in blacklist_set:
                return True
            parts = hostname.split(".")
            for i in range(1, len(parts) - 1):
                parent = ".".join(parts[i:])
                if parent in blacklist_set:
                    return True
    if name:
        name_lower = name.lower().strip()
        if name_lower in blacklist_set:
            return True
    return False

def _check_dns_sync(hostname: str) -> bool:
    try:
        socket.getaddrinfo(hostname, None)
        return True
    except (socket.gaierror, socket.timeout, Exception):
        return False

async def is_domain_reachable(url: str, blacklist_set: set = None) -> bool:
    """Non-blocking DNS check with in-memory caching."""
    hostname = urlparse(url).netloc.lower().strip()
    if not hostname:
        return False
    
    if hostname in _DNS_CACHE:
        return _DNS_CACHE[hostname]
    
    loop = asyncio.get_running_loop()
    try:
        reachable = await loop.run_in_executor(None, _check_dns_sync, hostname)
    except Exception:
        reachable = True
    _DNS_CACHE[hostname] = reachable
    return reachable

# Errors that indicate a permanently broken domain — auto-blacklist these.
FATAL_NAV_ERRORS = (
    "ERR_CERT_COMMON_NAME_INVALID",
    "ERR_CERT_DATE_INVALID",
    "ERR_CERT_AUTHORITY_INVALID",
    "ERR_SSL_VERSION_OR_CIPHER_MISMATCH",
    "ERR_HTTP2_PROTOCOL_ERROR",
    "ERR_SSL_PROTOCOL_ERROR",
)

# SPA hosts that require networkidle instead of domcontentloaded
SPA_HOSTS = ("notion.site", "notion.so", "layoffsandhires.com")

NON_JOB_URL_PATTERNS = [
    r'/c/[^/]+-jobs',
    r'/categories(?:/|$)',
    r'/category(?:/|$)',
    r'/jobcart(?:/|$)',
    r'/locations(?:/|$)',
    r'/early-careers(?:/|$)',
    r'/candidate-resources(?:/|$)',
    r'/benefits(?:/|$)',
    r'/life-at-[^/]+',
    r'/about-us(?:/|$)',
    r'/our-culture(?:/|$)',
    r'/saved-jobs(?:/|$)',
    r'/search-results(?:/|$)',
]

def is_non_job_url(url: str) -> bool:
    """Detect category/landing/informational URLs that are not specific job postings."""
    if not url:
        return False
    u_lower = url.lower()
    for pattern in NON_JOB_URL_PATTERNS:
        if re.search(pattern, u_lower):
            return True
    return False

def _wait_strategy(url: str) -> str:
    """Return the appropriate Playwright wait_until strategy for a given URL."""
    return "networkidle" if any(h in url for h in SPA_HOSTS) else "domcontentloaded"

def _get_timeout(url: str) -> int:
    """Longer timeout for SPA hosts that load slowly."""
    return 45000 if any(h in url for h in SPA_HOSTS) else 30000

def auto_blacklist(url: str, error_str: str, blacklist_set: set = None) -> None:
    """Append the hostname to blacklist.json when a fatal TLS/protocol error occurs."""
    is_fatal = any(code in error_str for code in FATAL_NAV_ERRORS)
    if not is_fatal:
        return
    hostname = urlparse(url).netloc.lower().strip()
    if not hostname:
        return
    if blacklist_set is not None:
        if hostname in blacklist_set:
            return
        blacklist_set.add(hostname)
    try:
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            bl = json.load(f)
        if not isinstance(bl, list):
            bl = []
        if hostname not in bl:
            bl.append(hostname)
            bl.sort()
            with open(BLACKLIST_FILE, "w", encoding="utf-8") as f:
                json.dump(bl, f, indent=4)
            print(f"[!] Auto-blacklisted {hostname} ({error_str[:50]}).")
    except Exception as ex:
        print(f"[!] Could not update blacklist: {ex}")

async def extract_links_smart_fallback(page, url, name, comp_country=None, priority=2):
    """Extract job posting links using link heuristics when selectors are missing or drifted."""
    try:
        current_url = page.url
        expected_host = urlparse(url).netloc
        if not current_url or expected_host not in current_url:
            print(f"      [!] Page redirected away from {url} (now at {current_url}), skipping link extraction.")
            return []
        links_data = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll("a")).map(a => ({
                href: a.getAttribute("href") || a.href || "",
                text: a.innerText || ""
            }));
        }""")
    except Exception as e:
        print(f"      [!] Error extracting links: {e}")
        return []

    jobs = []
    keywords = ["/job", "/career", "/req", "/position", "jobid=", "opening", "opportunity", "role"]
    for data in links_data:
        href = data.get("href", "")
        text = data.get("text", "")
        if href and text and text.strip():
            href_lower = href.lower()
            if any(k in href_lower for k in keywords):
                if "search" not in href_lower and "login" not in href_lower and "mailto:" not in href_lower and not is_non_job_url(href):
                    full_url = href if href.startswith('http') else urljoin(url, href)
                    if not is_non_job_url(full_url) and is_likely_job_url(full_url, url):
                        jobs.append({
                            "title": text.strip(),
                            "company": name,
                            "url": full_url,
                            "location": "",
                            "country": comp_country,
                            "priority": priority
                        })

    unique_jobs = {}
    for j in jobs:
        if j["url"] not in unique_jobs:
            unique_jobs[j["url"]] = j
    return list(unique_jobs.values())


async def scrape_company(context, company, semaphore, blacklist_set=None, telemetry=None, throttle=None):
    name = company["name"]
    url = company["careers_url"]

    # Skip blacklisted companies/domains
    if blacklist_set and is_blacklisted(url, name, blacklist_set):
        if telemetry:
            telemetry.record_blacklist_skip(name, "Careers URL blacklisted")
        return []

    # Check circuit breaker cooldown
    if throttle:
        in_cd, rem, reason = throttle.is_in_cooldown(url)
        if in_cd:
            if telemetry:
                telemetry.record_block(name, url, "Cooldown Bypassed", f"{reason} ({rem:.0f}s left)")
            return []

    # Non-blocking DNS check before spinning up a browser page
    if not await is_domain_reachable(url, blacklist_set):
        if telemetry:
            telemetry.record_block(name, url, "DNS / Unreachable", "DNS check failed")
        return []
    
    async with semaphore:
        if throttle:
            acquired = await throttle.acquire(url)
            if not acquired:
                if telemetry:
                    telemetry.record_block(name, url, "Cooldown Bypassed", "Domain in active cooldown")
                return []

        page = None
        try:
            page = await context.new_page()
            print(f"\n[*] Scraping Company: {name}...")
            print(f"[*] Navigating to {url}")
            wait_strat = _wait_strategy(url)
            nav_timeout = _get_timeout(url)
            response = None
            try:
                response = await page.goto(url, wait_until=wait_strat, timeout=nav_timeout)
                await asyncio.sleep(2)
            except Exception as e:
                error_str = str(e)
                print(f"[!] Warning: Navigation to {url} timed out or failed. {error_str}")
                if telemetry:
                    telemetry.record_block(name, url, "Navigation Timeout / Error", error_str[:120])
                await page.close()
                return []
            
            # Check HTTP status block
            if response:
                block_code = detect_http_block(response.status)
                if block_code:
                    print(f"[!] Site {name} returned blocking HTTP status {response.status} ({block_code})")
                    if throttle and response.status == 429:
                        throttle.trip_circuit_breaker(url, "HTTP 429 Rate Limited", cooldown_seconds=300)
                    if telemetry:
                        telemetry.record_block(name, url, block_code, f"HTTP {response.status}")
                    await page.close()
                    return []
            
            # Check DOM challenges / bot shields & attempt transient resolution
            page_title = ""
            page_text = ""
            try:
                page_title = await page.title()
                page_text = await page.evaluate("() => document.body ? document.body.innerText.substring(0, 3000) : ''")
                dom_block = detect_dom_challenge(page_title, page_text, page.url)
                if dom_block:
                    cleared = await resolve_transient_challenge(page, timeout_seconds=4.0)
                    if not cleared:
                        print(f"[!] Site {name} detected as blocked: {dom_block}")
                        if telemetry:
                            telemetry.record_block(name, page.url, dom_block, f"Title: {page_title}")
                        await page.close()
                        return []
            except Exception:
                pass
            
            # Detect page capacity if present
            pinfo = extract_page_count(page_text)
            if pinfo["page_count"] > 1 or pinfo["total_jobs"]:
                if telemetry:
                    telemetry.record_page_count(name, pinfo["page_count"], pinfo.get("total_jobs"))
            
            card_sel = company.get("job_card_selector")
            jobs = []
            comp_countries = company.get("countries")
            comp_country = comp_countries[0] if isinstance(comp_countries, list) and comp_countries else (comp_countries if isinstance(comp_countries, str) else None)
            
            if not card_sel:
                print(f"[*] No selectors defined for {name}. Using smart fallback to find job links...")
                jobs = await extract_links_smart_fallback(page, url, name, comp_country, priority=2)
                print(f"[*] Smart fallback found {len(jobs)} potential job links.")
                await page.close()
                return jobs[:30]

            cards = []
            try:
                await page.wait_for_selector(card_sel, timeout=7000)
                cards = await page.locator(card_sel).all()
            except Exception:
                cards = []

            if not cards:
                log(f"[!] Primary card selector '{card_sel}' failed for {name}. Attempting smart fallback...")
                fb_jobs = await extract_links_smart_fallback(page, url, name, comp_country, priority=2)
                if fb_jobs:
                    print(f"  [*] [HEURISTIC] Rescued {len(fb_jobs)} jobs for {name} using link heuristics.")
                    if telemetry:
                        telemetry.record_selector_drift(name, url, "card_selector", card_sel, f"Rescued {len(fb_jobs)} jobs via fallback", rescued=True, rescued_count=len(fb_jobs))
                    await page.close()
                    return fb_jobs[:30]
                else:
                    log(f"[!] Could not find any job cards ('{card_sel}') or links on this page.")
                    if telemetry:
                        telemetry.record_selector_drift(name, url, "card_selector", card_sel, "0 jobs found (card selector + fallback failed)", rescued=False)
                    await page.close()
                    return []
            log(f"[*] Found {len(cards)} job postings for {name}. Analyzing...")
            
            for idx, card in enumerate(cards[:30]):
                log(f"    - Processing card {idx+1}/{min(len(cards), 30)}...")
                try:
                    card_text = await card.text_content()
                    if card_text:
                        clower = card_text.lower()
                        old_phrases = ["30+ days", "30 days", "month ago", "months ago", "60 days", "90 days"]
                        if any(p in clower for p in old_phrases):
                            log(f"  [-] Skipping old job (found date text in card)")
                            continue

                    loc_sel = company.get("location_selector")
                    comp_loc = ""
                    if loc_sel:
                        try:
                            loc_el = card.locator(loc_sel).first
                            if await loc_el.count():
                                comp_loc = (await loc_el.text_content() or "").strip()
                        except Exception:
                            pass
                    if not comp_loc:
                        for fallback_sel in [".job-search-card__location", ".base-search-card__metadata span", ".companyLocation", "[data-testid='text-location']", ".job-location", ".location"]:
                            try:
                                f_el = card.locator(fallback_sel).first
                                if await f_el.count():
                                    txt = (await f_el.text_content() or "").strip()
                                    if txt and len(txt) > 2 and "ago" not in txt.lower() and "apply" not in txt.lower():
                                        comp_loc = txt
                                        break
                            except Exception:
                                pass

                    title_sel = company.get("title_selector")
                    title = ""
                    if title_sel:
                        try:
                            title_el = card.locator(title_sel).first
                            if await title_el.count():
                                title = (await title_el.text_content() or "").strip()
                        except Exception:
                            pass
                    if not title:
                        card_txt = (await card.text_content() or "").strip()
                        if card_txt:
                            title = card_txt.split("\n")[0].strip()
                    if not title:
                        title = "Unknown Title"
                    
                    c_sel = company.get("company_selector")
                    if c_sel and await card.locator(c_sel).count():
                        company_text = await card.locator(c_sel).first.text_content()
                    else:
                        company_text = name
                        
                    job_href = None
                    try:
                        card_tag = await card.evaluate("el => el.tagName.toLowerCase()")
                        if card_tag == "a":
                            c_href = await card.get_attribute("href")
                            if c_href:
                                job_href = c_href
                    except Exception:
                        pass

                    if not job_href:
                        url_el = card.locator(company.get("job_url_selector") or "a").first
                        if await url_el.count():
                            job_href = await url_el.get_attribute("href")
                    
                    if not job_href:
                        links = await card.locator("a").all()
                        for link in links:
                            href = await link.get_attribute("href")
                            if href and is_likely_job_url(href, url):
                                job_href = href
                                break

                    if not job_href:
                        job_href = await extract_fallback_link(card, url)
                                
                    if job_href and not job_href.startswith('http'):
                        job_href = urljoin(url, job_href)
                        
                    if not job_href or not is_likely_job_url(job_href, url) or is_non_job_url(job_href):
                        if telemetry:
                            telemetry.record_selector_drift(name, url, "link_selector", company.get("job_url_selector") or "a", "No valid job link found; card dropped")
                        continue

                    jobs.append({
                        "title": title.strip(),
                        "company": company_text.strip(),
                        "url": job_href,
                        "location": comp_loc,
                        "country": comp_country,
                        "priority": 1
                    })
                except Exception:
                    continue
            
            await page.close()
            return jobs
        finally:
            if throttle:
                throttle.release(url)


async def scrape_site(context, site_name, site_info, config, search_term, location, semaphore, telemetry=None, target_page=1, skip_page_one=False, detect_pages_only=False, throttle=None):
    search_url_pattern = config.get("search_url")
    if not search_url_pattern: 
        log(f"[!] No search_url pattern for {site_name}")
        return []
        
    effective_page = target_page
    if skip_page_one and effective_page == 1:
        effective_page = 2

    base_url = search_url_pattern.replace("{search_term}", search_term.replace(" ", "%20"))
    base_url = base_url.replace("{location}", location.replace(" ", "%20"))
    url = build_page_url(base_url, config, effective_page, site_name=site_name)

    # Check circuit breaker cooldown
    if throttle:
        in_cd, rem, reason = throttle.is_in_cooldown(url)
        if in_cd:
            if telemetry:
                telemetry.record_block(site_name, url, "Cooldown Bypassed", f"{reason} ({rem:.0f}s left)")
            return []

    async with semaphore:
        if throttle:
            acquired = await throttle.acquire(url)
            if not acquired:
                if telemetry:
                    telemetry.record_block(site_name, url, "Cooldown Bypassed", "Domain in active cooldown")
                return []

        page = None
        try:
            page = await context.new_page()
            log(f"  [*] Starting: {site_name} ('{search_term}' in '{location}' - Page {effective_page})")
            print(f"[*] Navigating to {url}")
            wait_strat = _wait_strategy(url)
            nav_timeout = _get_timeout(url)
            response = None
            try:
                response = await page.goto(url, wait_until=wait_strat, timeout=nav_timeout)
                await asyncio.sleep(2)
            except Exception as e:
                error_str = str(e)
                print(f"[!] Warning: Navigation to {url} timed out or failed. {error_str}")
                if telemetry:
                    telemetry.record_block(site_name, url, "Navigation Timeout / Error", error_str[:120])
                await page.close()
                return []

            # Check HTTP status block
            if response:
                block_code = detect_http_block(response.status)
                if block_code:
                    print(f"[!] Site {site_name} returned blocking HTTP status {response.status} ({block_code})")
                    if throttle and response.status == 429:
                        throttle.trip_circuit_breaker(url, "HTTP 429 Rate Limited", cooldown_seconds=300)
                    if telemetry:
                        telemetry.record_block(site_name, url, block_code, f"HTTP {response.status}")
                    await page.close()
                    return []

            # Check DOM challenges & attempt transient challenge resolution
            page_title = ""
            page_text = ""
            try:
                page_title = await page.title()
                page_text = await page.evaluate("() => document.body ? document.body.innerText.substring(0, 3000) : ''")
            except Exception:
                pass

            dom_block = detect_dom_challenge(page_title, page_text, page.url)
            if dom_block:
                cleared = await resolve_transient_challenge(page, timeout_seconds=4.0)
                if not cleared:
                    print(f"[!] Site {site_name} detected as blocked: {dom_block}")
                    if telemetry:
                        telemetry.record_block(site_name, page.url, dom_block, f"Title: {page_title}")
                    await page.close()
                    return []

            # Extract page count & capacity telemetry
            pagination_sel = config.get("pagination_selector")
            pagination_links = []
            if pagination_sel:
                try:
                    elements = await page.locator(pagination_sel).all()
                    for el in elements:
                        txt = (await el.text_content() or "").strip()
                        if txt:
                            pagination_links.append(txt)
                except Exception:
                    pass
            items_per_page = config.get("items_per_page", 25)
            pinfo = extract_page_count(page_text, pagination_links, items_per_page=items_per_page)
            if telemetry:
                telemetry.record_page_count(site_name, pinfo["page_count"], pinfo.get("total_jobs"))

            if detect_pages_only:
                print(f"  [*] [Detect-Only] {site_name}: {pinfo['page_count']} page(s) detected (~{pinfo.get('total_jobs')} listings)")
                await page.close()
                return []
                
            # If site requires dynamic search input typing (e.g. Layoffs & Hires)
            search_input_sel = config.get("search_input_selector")
            if search_input_sel:
                try:
                    await page.wait_for_selector(search_input_sel, timeout=7000)
                    input_el = page.locator(search_input_sel).first
                    if await input_el.count():
                        log(f"  [*] Typing search query '{search_term}' into '{search_input_sel}'...")
                        await input_el.fill(search_term)
                        await asyncio.sleep(1.0)
                except Exception as e:
                    log(f"[!] Warning: Failed to type into search input '{search_input_sel}': {e}")

            # Wait for job cards to load
            card_sel = config.get("job_card_selector")
            cards = []
            if card_sel:
                try:
                    await page.wait_for_selector(card_sel, timeout=7000)
                    cards = await page.locator(card_sel).all()
                except Exception:
                    cards = []

            # If site has an expandable results pane (e.g. Layoffs & Hires "Show more" button)
            expand_btn_sel = config.get("expand_button_selector")
            if expand_btn_sel:
                try:
                    expand_btn = page.locator(expand_btn_sel).first
                    if await expand_btn.count():
                        btn_txt = (await expand_btn.text_content() or "").strip()
                        log(f"  [*] Expanding results via '{expand_btn_sel}' ({btn_txt})...")
                        await expand_btn.click()
                        await asyncio.sleep(0.5)
                        if card_sel:
                            cards = await page.locator(card_sel).all()
                except Exception as e:
                    log(f"  [-] Expand button '{expand_btn_sel}' not clicked or not present: {e}")

            if not cards:
                rescued_sel, fb_cards = await find_fallback_cards(page)
                if fb_cards:
                    print(f"  [*] [HEURISTIC] Primary selector '{card_sel}' yielded 0 cards for {site_name}. Rescued {len(fb_cards)} cards using '{rescued_sel}'.")
                    cards = fb_cards
                    if telemetry:
                        telemetry.record_selector_drift(site_name, url, "card_selector", card_sel or "None", f"Rescued {len(cards)} cards using '{rescued_sel}'", rescued=True, rescued_count=len(cards))
                else:
                    print(f"[!] Could not find any job cards ('{card_sel}') on this page.")
                    if telemetry:
                        telemetry.record_selector_drift(site_name, url, "card_selector", card_sel or "None", "0 cards found (primary + fallback failed)", rescued=False)
                    await page.close()
                    return []

            log(f"[*] Found {len(cards)} job cards. Analyzing...")
            
            max_cards = config.get("max_cards", 60 if config.get("expand_button_selector") else 30)
            jobs = []
            for idx, card in enumerate(cards[:max_cards]):
                log(f"    - Processing card {idx+1}/{min(len(cards), max_cards)}...")
                try:
                    card_text = await card.text_content()
                    if card_text:
                        clower = card_text.lower()
                        old_phrases = ["30+ days", "30 days", "month ago", "months ago", "60 days", "90 days"]
                        if any(p in clower for p in old_phrases):
                            continue

                    title_sel = config.get("title_selector")
                    title = ""
                    if title_sel:
                        try:
                            title_el = card.locator(title_sel).first
                            if await title_el.count():
                                title = (await title_el.text_content() or "").strip()
                        except Exception:
                            pass
                    if not title or title == "Unknown Title":
                        fb_title = await extract_fallback_title(card)
                        if fb_title:
                            title = fb_title
                        else:
                            title = "Unknown Title"
                            if telemetry:
                                telemetry.record_selector_drift(site_name, url, "title_selector", title_sel or "None", "Fell back to 'Unknown Title'")

                    comp_sel = config.get("company_selector")
                    company = ""
                    if comp_sel:
                        try:
                            company_el = card.locator(comp_sel).first
                            if await company_el.count():
                                company = (await company_el.text_content() or "").strip()
                        except Exception:
                            pass
                    if not company or company == "Unknown Company":
                        fb_comp = await extract_fallback_company(card, candidate_title=title)
                        if fb_comp:
                            company = fb_comp
                        else:
                            company = "Unknown Company"
                    
                    loc_sel = config.get("location_selector")
                    card_location = ""
                    if loc_sel:
                        try:
                            loc_el = card.locator(loc_sel).first
                            if await loc_el.count():
                                card_location = (await loc_el.text_content() or "").strip()
                        except Exception:
                            pass
                    if not card_location:
                        card_location = await extract_fallback_location(card)

                    job_href = None
                    try:
                        card_tag = await card.evaluate("el => el.tagName.toLowerCase()")
                        if card_tag == "a":
                            c_href = await card.get_attribute("href")
                            if c_href:
                                job_href = c_href
                    except Exception:
                        pass

                    if not job_href:
                        links = await card.locator("a").all()
                        for link in links:
                            href = await link.get_attribute("href")
                            if href and ("/job/" in href or "/post/" in href or "/jobs/" in href):
                                if not is_non_job_url(href):
                                    job_href = href
                                    break
                    
                    if not job_href:
                        j_sel = config.get("job_url_selector")
                        if j_sel:
                            url_el = card.locator(j_sel).first
                            if await url_el.count():
                                job_href = await url_el.get_attribute("href")

                    if not job_href:
                        job_href = await extract_fallback_link(card, url)
                    
                    if job_href and not job_href.startswith('http'):
                        job_href = urljoin(url, job_href)
                        
                    if not job_href or not is_likely_job_url(job_href, url, allow_career_portals=config.get("is_career_directory", False)) or is_non_job_url(job_href):
                        if telemetry:
                            telemetry.record_selector_drift(site_name, url, "link_selector", config.get("job_url_selector") or "a", "No valid job link found; card dropped to prevent search URL poisoning")
                        continue

                    title = title.strip()
                    if company and company.strip() and company.strip() != "Unknown Company":
                        company = company.strip()
                    else:
                        try:
                            all_text_elements = await card.locator("span").all_text_contents()
                            for t in all_text_elements:
                                if t and len(t.strip()) > 3 and "Apply" not in t and "ago" not in t and t.strip() != card_location:
                                    company = t.strip()
                                    break
                        except Exception:
                            pass

                    # Directory format specialization (e.g. Layoffs & Hires)
                    if config.get("is_career_directory"):
                        if not company or company == "Unknown Company":
                            company = title
                        job_count_str = ""
                        try:
                            cnt_el = card.locator(".matches-n, [class*='is-hire'], [class*='num']").first
                            if await cnt_el.count():
                                job_count_str = (await cnt_el.text_content() or "").strip()
                        except Exception:
                            pass
                        title = f"{search_term} ({job_count_str})" if job_count_str else f"{search_term} ({company})"
                        if not card_location:
                            card_location = location
                    
                    jobs.append({
                        "title": title,
                        "company": company,
                        "url": job_href,
                        "location": card_location,
                        "country": None,
                        "searched_location": location,
                        "priority": 1
                    })
                except Exception as e:
                    print(f"[!] Error parsing card {idx}: {e}")
                    continue
                    
            await page.close()
            print(f"  [+] Finished: {site_name} ('{search_term}' in '{location}' - Page {effective_page}). Found {len(jobs)} jobs.")
            return jobs
        finally:
            if throttle:
                throttle.release(url)


async def fetch_job_description(context, job_url, semaphore, blacklist_set=None, telemetry=None, throttle=None):
    if blacklist_set and is_blacklisted(job_url, "", blacklist_set):
        if telemetry:
            telemetry.record_blacklist_skip(job_url, "JD URL blacklisted")
        return ""

    if throttle:
        in_cd, rem, reason = throttle.is_in_cooldown(job_url)
        if in_cd:
            if telemetry:
                telemetry.record_block("Unknown", job_url, "Cooldown Bypassed", f"{reason} ({rem:.0f}s left)")
            return ""

    if not await is_domain_reachable(job_url, blacklist_set):
        if telemetry:
            telemetry.record_block("Unknown", job_url, "DNS / Unreachable", "Domain unreachable for JD")
        return ""

    async with semaphore:
        if throttle:
            acquired = await throttle.acquire(job_url)
            if not acquired:
                if telemetry:
                    telemetry.record_block("Unknown", job_url, "Cooldown Bypassed", "Domain in active cooldown")
                return ""

        page = None
        try:
            page = await context.new_page()
            description = ""
            print(f"  [-] Fetching JD from {job_url}")
            response = await page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
            
            if response:
                block_code = detect_http_block(response.status)
                if block_code:
                    if throttle and response.status == 429:
                        throttle.trip_circuit_breaker(job_url, "HTTP 429 Rate Limited", cooldown_seconds=300)
                    if telemetry:
                        telemetry.record_block("Unknown", job_url, block_code, f"HTTP {response.status}")
                    await page.close()
                    return ""

            page_title = await page.title()
            body_sample = await page.evaluate("() => document.body ? document.body.innerText.substring(0, 1000) : ''")
            dom_block = detect_dom_challenge(page_title, body_sample, page.url)
            if dom_block:
                cleared = await resolve_transient_challenge(page, timeout_seconds=4.0)
                if not cleared:
                    if telemetry:
                        telemetry.record_block("Unknown", job_url, dom_block, f"Title: {page_title}")
                    await page.close()
                    return ""

            description = await page.evaluate('''() => {
                const noiseSelectors = [
                    'nav', 'footer', 'aside', 'header', 'button', 'script', 'style',
                    '.nav', '.footer', '.header', '.menu', '.sidebar', '.ad',
                    '[role="banner"]', '[role="navigation"]', '[role="contentinfo"]'
                ];
                
                const body = document.body.cloneNode(true);
                noiseSelectors.forEach(sel => {
                    const elements = body.querySelectorAll(sel);
                    elements.forEach(el => el.remove());
                });
                
                const main = body.querySelector('main') || body.querySelector('article') || body.querySelector('[role="main"]');
                if (main) {
                    return main.innerText;
                }
                
                return body.innerText;
            }''')
            return description
        except Exception as e:
            print(f"  [!] Failed to load JD: {e}")
            if telemetry:
                telemetry.record_block("Unknown", job_url, "JD Fetch Error", str(e)[:100])
            return ""
        finally:
            if page:
                await page.close()
            if throttle:
                throttle.release(job_url)


MAX_CONCURRENT_PAGES = 10

async def discover_jobs_from_config(context, config, semaphore, blacklist_set=None, telemetry=None, target_page=1, skip_page_one=False, max_pages=1, detect_pages_only=False, throttle=None):
    site_name = config["site_name"]
    url = config.get("url") or config.get("search_url") or ""
    
    if blacklist_set and is_blacklisted(url, site_name, blacklist_set):
        if telemetry:
            telemetry.record_blacklist_skip(site_name, "Job board blacklisted")
        return []

    search_terms = config.get("search_terms") or ["Senior QA Engineer"]
    locations = config.get("locations") or ["Seattle"]
    
    effective_start = 2 if (skip_page_one and target_page == 1) else target_page
    pages_to_scrape = range(effective_start, effective_start + max_pages)

    tasks = []
    for search_term in search_terms:
        for location in locations:
            for p_num in pages_to_scrape:
                tasks.append(scrape_site(
                    context, site_name, config, config, search_term, location, semaphore,
                    telemetry=telemetry, target_page=p_num, skip_page_one=False,
                    detect_pages_only=detect_pages_only, throttle=throttle
                ))
            
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_discovered = []
    for res in results:
        if isinstance(res, Exception):
            log(f"  [!] Internal search failed for {site_name}: {res}")
        else:
            for job in res:
                job["site"] = site_name
            all_discovered.extend(res)
            
    return all_discovered

async def discover_jobs_from_company(context, company, semaphore, blacklist_set=None, telemetry=None, throttle=None):
    site_name = company["name"]
    jobs = await scrape_company(context, company, semaphore, blacklist_set=blacklist_set, telemetry=telemetry, throttle=throttle)
    for job in jobs:
        job["site"] = site_name
    return jobs

async def process_discovered_job(context, job, semaphore, processed_urls, blacklist_set=None, telemetry=None, dry_run=False, throttle=None):
    if not job["url"] or job["url"] in processed_urls:
        return None
        
    processed_urls.add(job["url"])
    
    if is_non_job_url(job["url"]):
        print(f"  [-] Skipping non-job landing page URL: {job['url']}")
        return None

    if throttle:
        in_cd, rem, reason = throttle.is_in_cooldown(job["url"])
        if in_cd:
            if telemetry:
                telemetry.record_block(job.get("site", "Unknown"), job["url"], "Cooldown Bypassed", f"{reason} ({rem:.0f}s left)")
            return None

    if is_duplicate(job["url"], job["title"], job["company"]):
        print(f"  [-] Skipping existing job: {job['title']} at {job['company']}")
        return None
        
    # If we already have the description from the ATS API, use it. Otherwise, fetch it.
    jd_text = job.get("description", "")
    if not jd_text:
        try:
            jd_text = await asyncio.wait_for(fetch_job_description(context, job["url"], semaphore, blacklist_set=blacklist_set, telemetry=telemetry, throttle=throttle), timeout=45)
        except asyncio.TimeoutError:
            print(f"  [!] Timeout fetching JD for {job['url']}")
            if telemetry:
                telemetry.record_block(job.get("site", "Unknown"), job["url"], "JD Fetch Timeout", "Exceeded 45s")
            return None
    
    active_profile = get_active_profile()
    filter_results = score_job(
        jd_text,
        title=job.get("title", ""),
        location=job.get("location", ""),
        country=job.get("country", ""),
        company=job.get("company", ""),
        url=job.get("url", ""),
        profile_data=active_profile
    )
    job["filter_results"] = filter_results
    
    if filter_results.get("is_disqualified"):
        reasons = filter_results.get("disqualified_by", [])
        reasons_str = ", ".join(reasons)
        print(f"  [-] Job Disqualified: {job['title']} at {job['company']} (Reasons: {reasons_str})")
        if telemetry:
            telemetry.record_rejection(job.get("title", "Unknown"), job.get("company", "Unknown"), reasons)
        return job
        
    score = filter_results.get("score", 75)
    missing_skills = filter_results.get("missing_skills", [])[:3]
    matched_skills = filter_results.get("matched_skills", [])[:5] 
    profile_id = filter_results.get("score_profile_id")
    
    if not dry_run:
        add_job(
            job["title"],
            job["company"],
            job["url"],
            job["site"],
            score,
            missing_skills,
            matched_skills,
            score_profile_id=profile_id,
            location=job.get("location"),
            country=job.get("country") or filter_results.get("detected_country")
        )
    else:
        print(f"  [DRY RUN] Would add job: {job['title']} at {job['company']} (Score: {score})")

    if telemetry:
        telemetry.record_job_passed(1)

    return job


async def worker(context, queue, semaphore, processed_urls, results, blacklist_set=None, telemetry=None, dry_run=False, throttle=None):
    """A worker task that drains the job queue."""
    while not queue.empty():
        job = await queue.get()
        try:
            res = await process_discovered_job(
                context, job, semaphore, processed_urls,
                blacklist_set=blacklist_set, telemetry=telemetry, dry_run=dry_run, throttle=throttle
            )
            if res:
                results.append(res)
        except Exception as e:
            log(f"  [!] Worker error processing {job.get('url')}: {e}")
        finally:
            queue.task_done()

async def main(args=None):
    import aiohttp
    from scripts.ats_adapters.index import route_company
    
    cli_args = parse_args(args)
    telemetry = ScourTelemetry()
    throttle = DomainThrottle()
    
    seed_default_profile()
    search_configs = get_all_search_configs()
    selectors_cache = load_json(CONFIG_FILE)
    if isinstance(selectors_cache, dict):
        for cfg in search_configs:
            sname = cfg.get("site_name")
            if sname and sname in selectors_cache:
                for k, v in selectors_cache[sname].items():
                    if k not in cfg or cfg[k] is None or cfg[k] == "":
                        cfg[k] = v
    companies = get_all_companies()
    blacklist = load_json(BLACKLIST_FILE)
    if not isinstance(blacklist, list):
        blacklist = []
    blacklist_set = {b.lower().strip() for b in blacklist if b}
    
    # Also include dead domains from quarantine if available
    quarantined = load_json("quarantined_domains.json")
    if isinstance(quarantined, list):
        for q in quarantined:
            dom = q.get("domain", "").lower().strip() if isinstance(q, dict) else (q.lower().strip() if isinstance(q, str) else "")
            if dom:
                blacklist_set.add(dom)
    
    if not search_configs and not companies:
        print("[!] No search configurations or companies found in the database. Please add some first.")
        return
        
    # Clean logs before scraping
    clean_logs("logs")
    
    # Pre-filter search_configs upfront
    active_search_configs = []
    skipped_configs = 0
    for cfg in search_configs:
        cfg_url = cfg.get("url") or cfg.get("search_url") or ""
        cfg_name = cfg.get("site_name") or ""
        if is_blacklisted(cfg_url, cfg_name, blacklist_set):
            skipped_configs += 1
            telemetry.record_blacklist_skip(cfg_name, "Search config blacklisted")
        else:
            active_search_configs.append(cfg)
    if skipped_configs > 0:
        log(f"[*] Pre-filtered {skipped_configs} blacklisted job boards upfront ({len(active_search_configs)} active).")

    # Pre-filter companies upfront
    active_ats_companies = []
    active_direct_companies = []
    skipped_companies = 0
    for company in companies:
        name = company.get("name", "")
        url = company.get("careers_url", "") or company.get("ats_url", "")
        if is_blacklisted(url, name, blacklist_set):
            skipped_companies += 1
            telemetry.record_blacklist_skip(name, "Company URL blacklisted")
            continue
        if company.get("ats_type"):
            active_ats_companies.append(company)
        else:
            active_direct_companies.append(company)
            
    if skipped_companies > 0:
        log(f"[*] Pre-filtered {skipped_companies} blacklisted companies upfront ({len(active_ats_companies)} ATS, {len(active_direct_companies)} direct).")
    
    all_discovered = []
    
    # Phase 0: Fast ATS API Harvesting (No browser)
    if not cli_args.detect_pages_only and not cli_args.skip_page_one and cli_args.page == 1:
        log("\n=== Phase 0: Discovering Jobs via ATS APIs (Fast Mode) ===")
        if active_ats_companies:
            async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
                ats_tasks = []
                for company in active_ats_companies:
                    task = route_company(session, company["name"], company["ats_type"], company["ats_url"])
                    ats_tasks.append(task)
                    
                ats_results = await asyncio.gather(*ats_tasks, return_exceptions=True)
                for company, result in zip(active_ats_companies, ats_results):
                    if isinstance(result, Exception):
                        log(f"  [!] Failed to scrape ATS for {company['name']}: {result}")
                        telemetry.record_block(company["name"], company.get("ats_url", ""), "ATS API Error", str(result)[:100])
                    else:
                        for job in result:
                            job["site"] = company["name"]
                            job["priority"] = 0
                            all_discovered.append(job)
            log(f"[*] ATS API discovery complete. Found {len([j for j in all_discovered if j.get('priority') == 0])} jobs.")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Initialize with evasive stealth browser context
        context = await create_stealth_context(browser)
        
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAGES)
        processed_urls = set()
        
        # 1. DISCOVERY PHASE (Tiered)
        log("\n=== Phase 1a: Discovering Jobs (Job Boards) ===")
        site_tasks = []
        for config in active_search_configs:
            task = asyncio.wait_for(discover_jobs_from_config(
                context, config, semaphore, blacklist_set,
                telemetry=telemetry,
                target_page=cli_args.page,
                skip_page_one=cli_args.skip_page_one,
                max_pages=cli_args.max_pages,
                detect_pages_only=cli_args.detect_pages_only,
                throttle=throttle
            ), timeout=900)
            site_tasks.append(task)
            
        site_results_raw = await asyncio.gather(*site_tasks, return_exceptions=True)
        
        for i, res in enumerate(site_results_raw):
            if isinstance(res, Exception):
                log(f"[!] Phase 1a Site {i} failed or timed out: {res}")
            else:
                all_discovered.extend(res)
        
        log(f"\n[*] Job Board discovery complete. Found {len(all_discovered)} potential jobs.")

        if not cli_args.detect_pages_only and (not cli_args.skip_page_one or cli_args.page == 1):
            log("\n=== Phase 1b: Discovering Jobs (Company Careers) ===")
            company_tasks = []
            for company in active_direct_companies:
                task = asyncio.wait_for(discover_jobs_from_company(
                    context, company, semaphore, blacklist_set,
                    telemetry=telemetry, throttle=throttle
                ), timeout=120)
                company_tasks.append(task)
                
            company_results_raw = await asyncio.gather(*company_tasks, return_exceptions=True)
            
            company_count = 0
            for i, res in enumerate(company_results_raw):
                if isinstance(res, Exception):
                    continue
                else:
                    all_discovered.extend(res)
                    company_count += len(res)
            
            log(f"[*] Company discovery complete. Found {company_count} potential jobs.")

        log(f"\n[*] Total Discovery complete. Found {len(all_discovered)} potential jobs.")
        
        if cli_args.detect_pages_only:
            await browser.close()
            telemetry.record_throttle_metrics(throttle.get_metrics())
            telemetry.print_summary()
            telemetry.save_json("logs/scour_summary_latest.json")
            return

        # 2. PROCESSING PHASE (Prioritized Queue)
        log("\n=== Phase 2: Fetching Descriptions and Filtering (Prioritized Queue) ===")
        
        telemetry.record_job_discovered(len(all_discovered))
        all_discovered.sort(key=lambda x: x.get("priority", 1))
        
        job_queue = asyncio.Queue()
        for job in all_discovered:
            job_queue.put_nowait(job)
            
        log(f"[*] Processing {len(all_discovered)} jobs with {MAX_CONCURRENT_PAGES} workers...")
        
        results = []
        worker_tasks = []
        for _ in range(MAX_CONCURRENT_PAGES):
            task = asyncio.create_task(worker(
                context, job_queue, semaphore, processed_urls, results,
                blacklist_set=blacklist_set, telemetry=telemetry, dry_run=cli_args.dry_run, throttle=throttle
            ))
            worker_tasks.append(task)
            
        await job_queue.join()
        
        for task in worker_tasks:
            task.cancel()
            
        all_results = results
        telemetry.record_job_processed(len(all_results))
        
        await browser.close()
        
        # Attach throttle metrics to telemetry
        telemetry.record_throttle_metrics(throttle.get_metrics())
        telemetry.print_summary()
        
        # Save to logs
        os.makedirs("logs", exist_ok=True)
        telemetry.save_json("logs/scour_summary_latest.json")
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        telemetry.save_json(f"logs/scour_summary_{timestamp_str}.json")
        
        with open("logs/auto_scour_results.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)
        log("\n[*] Results saved to logs/auto_scour_results.json and logs/scour_summary_latest.json")
        
        if cli_args.dry_run:
            log("[*] [DRY RUN] Skipping updates to jobs_to_review.md and SQLite database.")
            return

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
                    for line in md_updates_passed:
                        job_url_match = re.search(r'\[Apply\]\((.*?)\)', line)
                        if job_url_match:
                            job_url = job_url_match.group(1)
                            if job_url not in table_part:
                                table_part += "\n" + line
                
                new_md = table_part + "\n\n## Disqualified Jobs"
                
                if md_updates_failed:
                    for line in md_updates_failed:
                        if line not in disq_part:
                            disq_part += "\n" + line
                
                new_md += disq_part
                
                with open("jobs_to_review.md", "w", encoding="utf-8") as f:
                    f.write(new_md)
            log(f"[*] Updated jobs_to_review.md")

if __name__ == "__main__":
    asyncio.run(main())
