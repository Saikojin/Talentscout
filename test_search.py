import asyncio
from playwright.async_api import async_playwright
import urllib.parse

async def test_search():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        print("Searching...")
        url = f"https://html.duckduckgo.com/html/?q=Simform+software+careers"
        await page.goto(url)
        # Check what the first link is
        try:
            await page.wait_for_selector('.result__url', timeout=5000)
            elem = await page.query_selector('.result__url')
            if elem:
                href = await elem.get_attribute('href')
                print("DDG Found:", href)
        except Exception as e:
            print("DDG search failed:", e)

        # Let's also try Bing
        url = f"https://www.bing.com/search?q=Simform+software+careers"
        await page.goto(url)
        try:
            await page.wait_for_selector('li.b_algo h2 a', timeout=5000)
            elem = await page.query_selector('li.b_algo h2 a')
            if elem:
                href = await elem.get_attribute('href')
                print("Bing Found:", href)
        except Exception as e:
            print("Bing search failed:", e)
            
        await browser.close()

asyncio.run(test_search())
