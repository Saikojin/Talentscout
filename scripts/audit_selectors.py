import argparse
import asyncio
import json
import os
import sys
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin, urlparse

# Ensure local imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from playwright.async_api import async_playwright
    from scripts.browser_stealth import create_stealth_context, resolve_transient_challenge
    from scripts.scour_telemetry import detect_http_block, detect_dom_challenge
    from scripts.selector_heuristics import (
        find_fallback_cards,
        extract_fallback_title,
        extract_fallback_link,
        extract_fallback_company,
        extract_fallback_location,
        is_likely_job_url,
    )
except ImportError as e:
    print(f"Error importing modules: {e}")

DEFAULT_CONFIG_PATH = "site_selectors.json"

async def audit_single_site(
    context,
    site_name: str,
    config: Dict[str, Any],
    keyword: str = "QA Engineer",
    location: str = "Seattle, WA",
    timeout_ms: int = 15000
) -> Dict[str, Any]:
    """
    Audit selectors for a single site config using Playwright.
    Returns diagnostic dict containing status, counts, sample data, and suggested fixes.
    """
    raw_url = config.get("search_url", "")
    if not raw_url:
        return {
            "site": site_name,
            "status": "CONFIG_ERROR",
            "error": "No search_url defined in config",
            "cards_found": 0
        }

    search_url = raw_url.format(search_term=keyword, location=location)
    page = await context.new_page()

    result = {
        "site": site_name,
        "search_url": search_url,
        "card_selector": config.get("job_card_selector"),
        "cards_found": 0,
        "fallback_card_selector": None,
        "fallback_cards_found": 0,
        "sample_title": None,
        "sample_url": None,
        "sample_company": None,
        "status": "UNKNOWN",
        "details": ""
    }

    try:
        response = None
        try:
            response = await page.goto(search_url, wait_until="domcontentloaded", timeout=timeout_ms)
            await asyncio.sleep(2)
        except Exception as e:
            result["status"] = "TIMEOUT"
            result["details"] = f"Navigation error/timeout: {str(e)[:100]}"
            await page.close()
            return result

        # 1. Check HTTP block
        if response:
            http_block = detect_http_block(response.status)
            if http_block:
                result["status"] = "BLOCKED"
                result["details"] = f"HTTP status {response.status} ({http_block})"
                await page.close()
                return result

        # 2. Check DOM challenge
        title = await page.title()
        body_text = await page.evaluate("() => document.body ? document.body.innerText.substring(0, 3000) : ''")
        dom_block = detect_dom_challenge(title, body_text, page.url)
        if dom_block:
            cleared = await resolve_transient_challenge(page, timeout_seconds=3.0)
            if not cleared:
                result["status"] = "BLOCKED"
                result["details"] = f"WAF/CAPTCHA: {dom_block}"
                await page.close()
                return result

        # 3. Test primary card selector
        card_sel = config.get("job_card_selector")
        cards = []
        if card_sel:
            try:
                await page.wait_for_selector(card_sel, timeout=5000)
                cards = await page.locator(card_sel).all()
            except Exception:
                cards = []

        result["cards_found"] = len(cards)

        # 4. If primary selector failed, probe fallback heuristics
        if not cards:
            fb_sel, fb_cards = await find_fallback_cards(page)
            if fb_cards:
                result["fallback_card_selector"] = fb_sel
                result["fallback_cards_found"] = len(fb_cards)
                result["status"] = "DRIFT_CARD"
                result["details"] = f"0 cards for '{card_sel}'. Heuristic found {len(fb_cards)} via '{fb_sel}'"
            else:
                result["status"] = "DRIFT_CARD"
                result["details"] = f"0 cards found for primary selector '{card_sel}' and no heuristic match"
            await page.close()
            return result

        # 5. Test sub-selectors on first card
        first_card = cards[0]

        # Title
        title_sel = config.get("title_selector")
        extracted_title = ""
        if title_sel:
            try:
                t_el = first_card.locator(title_sel).first
                if await t_el.count():
                    extracted_title = (await t_el.text_content() or "").strip()
            except Exception:
                pass
        if not extracted_title:
            fb_title = await extract_fallback_title(first_card)
            extracted_title = fb_title

        result["sample_title"] = extracted_title or "Unknown Title"

        # URL
        url_sel = config.get("job_url_selector")
        extracted_url = None
        try:
            card_tag = await first_card.evaluate("el => el.tagName.toLowerCase()")
            if card_tag == "a":
                extracted_url = await first_card.get_attribute("href")
                if extracted_url and not extracted_url.startswith("http"):
                    try:
                        res = await first_card.evaluate("el => el.href")
                        if res and res.startswith("http"):
                            extracted_url = res
                        else:
                            extracted_url = urljoin(page.url, extracted_url)
                    except Exception:
                        extracted_url = urljoin(page.url, extracted_url)
        except Exception:
            pass

        if not extracted_url and url_sel:
            try:
                u_el = first_card.locator(url_sel).first
                if await u_el.count():
                    extracted_url = await u_el.get_attribute("href")
                    if extracted_url and not extracted_url.startswith("http"):
                        try:
                            res = await u_el.evaluate("el => el.href")
                            if res and res.startswith("http"):
                                extracted_url = res
                            else:
                                extracted_url = urljoin(page.url, extracted_url)
                        except Exception:
                            extracted_url = urljoin(page.url, extracted_url)
            except Exception:
                pass

        if not extracted_url:
            extracted_url = await extract_fallback_link(first_card, page.url)

        if extracted_url and not extracted_url.startswith("http"):
            extracted_url = urljoin(page.url, extracted_url)

        result["sample_url"] = extracted_url

        # Company
        comp_sel = config.get("company_selector")
        extracted_company = ""
        if comp_sel:
            try:
                c_el = first_card.locator(comp_sel).first
                if await c_el.count():
                    extracted_company = (await c_el.text_content() or "").strip()
            except Exception:
                pass
        if not extracted_company:
            extracted_company = await extract_fallback_company(first_card, candidate_title=extracted_title)

        result["sample_company"] = extracted_company or "Unknown Company"

        # 6. Overall verdict
        if not extracted_url or not is_likely_job_url(extracted_url, search_url):
            result["status"] = "DRIFT_LINK"
            result["details"] = f"Cards found ({len(cards)}), but job_url_selector failed or matched search page URL"
        elif not extracted_title or extracted_title == "Unknown Title":
            result["status"] = "DRIFT_TITLE"
            result["details"] = f"Cards found ({len(cards)}), but title_selector failed to extract text"
        else:
            result["status"] = "PASS"
            result["details"] = f"Healthy: {len(cards)} cards extracted"

        await page.close()
        return result

    except Exception as e:
        result["status"] = "ERROR"
        result["details"] = str(e)[:120]
        try:
            await page.close()
        except Exception:
            pass
        return result


def format_audit_report(results: List[Dict[str, Any]]) -> str:
    """Format audit results as a high-density summary report table."""
    lines = [
        "",
        "=" * 85,
        "                     DOM SELECTOR AUDIT REPORT",
        "=" * 85,
        f"{'Site Name':<22} | {'Status':<12} | {'Cards':<6} | {'Sample Title':<28} | {'Notes'}",
        "-" * 85,
    ]

    pass_count = 0
    drift_count = 0
    block_count = 0
    error_count = 0

    for r in results:
        status = r.get("status", "UNKNOWN")
        if status == "PASS":
            pass_count += 1
        elif "DRIFT" in status:
            drift_count += 1
        elif status == "BLOCKED":
            block_count += 1
        else:
            error_count += 1

        site = r.get("site", "")[:21]
        cards = str(r.get("cards_found", 0))
        title = (r.get("sample_title") or "None")[:27]
        notes = r.get("details", "")[:40]

        lines.append(f"{site:<22} | {status:<12} | {cards:<6} | {title:<28} | {notes}")

    lines.append("-" * 85)
    lines.append(f"TOTAL AUDITED: {len(results)} | PASS: {pass_count} | DRIFT: {drift_count} | BLOCKED: {block_count} | OTHER: {error_count}")
    lines.append("=" * 85)
    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(description="TalentScout DOM Selector Auditor")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to site_selectors.json")
    parser.add_argument("--site", help="Audit a specific site name (case-insensitive substring)")
    parser.add_argument("--all", action="store_true", help="Audit all sites in the config")
    parser.add_argument("--keyword", default="QA Engineer", help="Search keyword (default: 'QA Engineer')")
    parser.add_argument("--location", default="Seattle, WA", help="Search location (default: 'Seattle, WA')")
    parser.add_argument("--timeout", type=int, default=15, help="Navigation timeout in seconds (default: 15)")
    parser.add_argument("--json-out", help="Path to save audit results JSON")
    parser.add_argument("--headless", action="store_true", default=True, help="Run headless (default: True)")
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"Error: Config file not found at {args.config}")
        sys.exit(1)

    with open(args.config, "r", encoding="utf-8") as f:
        site_configs = json.load(f)

    # Filter sites
    targets = {}
    if args.site:
        s_lower = args.site.lower()
        for name, cfg in site_configs.items():
            if s_lower in name.lower():
                targets[name] = cfg
        if not targets:
            print(f"No sites matching '{args.site}' found in {args.config}")
            sys.exit(1)
    elif args.all:
        targets = site_configs
    else:
        # Default: audit top job platforms
        default_platforms = ["LinkedIn", "Indeed", "BuiltIn", "Dice", "Glassdoor", "ZipRecruiter"]
        targets = {k: v for k, v in site_configs.items() if k in default_platforms}

    print(f"[*] Starting selector audit across {len(targets)} site(s)...")

    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=args.headless)
        context = await create_stealth_context(browser)

        for site_name, cfg in targets.items():
            print(f"  --> Auditing: {site_name}...")
            res = await audit_single_site(
                context,
                site_name,
                cfg,
                keyword=args.keyword,
                location=args.location,
                timeout_ms=args.timeout * 1000
            )
            results.append(res)
            # Brief pause between site audits
            await asyncio.sleep(1.5)

        await browser.close()

    print(format_audit_report(results))

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"[*] Saved audit results to {args.json_out}")

if __name__ == "__main__":
    asyncio.run(main())
