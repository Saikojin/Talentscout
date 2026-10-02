import asyncio
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from playwright.async_api import async_playwright
from scripts.auto_scour import scrape_company
from scripts.database import get_all_companies

async def test_scrape():
    companies = get_all_companies()
    target = None
    for c in companies:
        if c.get('name') == 'Chainguard':
            target = c
            break
            
    print(f"Testing company target: {target}")
    if not target:
        return
        
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        sem = asyncio.Semaphore(1)
        jobs = await scrape_company(context, target, sem)
        print(f"\nDiscovered {len(jobs)} jobs for {target['name']}:")
        for j in jobs[:10]:
            print(f"  * Title: {j['title']} | Loc: {j['location']} | URL: {j['url']}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_scrape())
