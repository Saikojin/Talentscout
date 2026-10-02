import asyncio
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.async_api import async_playwright
import aiohttp
from scripts.ats_adapters.index import route_company
from scripts.auto_scour import scrape_company
from scripts.database import get_all_companies

async def test_zapier_scrape():
    companies = get_all_companies()
    
    # Test an ATS company (e.g., Stripe, Discord, Miro, ClickUp)
    stripe = next((c for c in companies if c.get('name') == 'Stripe'), None)
    if stripe and stripe.get('ats_type'):
        print(f"[*] Testing ATS Adapter for {stripe['name']} ({stripe['ats_type']})...")
        async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
            jobs = await route_company(session, stripe['name'], stripe['ats_type'], stripe['ats_url'])
            print(f"    Discovered {len(jobs)} jobs via ATS API. First 3:")
            for j in jobs[:3]:
                print(f"      * {j['title']} | {j.get('location', '')} | {j['url']}")
                
    # Test a direct career page company (e.g., Intuit, AccuLynx, BambooHR)
    direct_target = next((c for c in companies if c.get('name') == 'AccuLynx'), None)
    if direct_target:
        print(f"\n[*] Testing Direct Scraper for {direct_target['name']}...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            sem = asyncio.Semaphore(1)
            jobs = await scrape_company(context, direct_target, sem)
            print(f"    Discovered {len(jobs)} jobs via Direct Scraper. First 3:")
            for j in jobs[:3]:
                print(f"      * {j['title']} | {j.get('location', '')} | {j['url']}")
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_zapier_scrape())
