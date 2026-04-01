import asyncio
from playwright.async_api import async_playwright
import sys
import os

# Append current dir to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.database import get_all_search_configs

async def test_dice():
    configs = get_all_search_configs()
    dice_config = next((c for c in configs if "dice" in c["site_name"].lower()), None)
    
    if not dice_config:
        print("Dice config not found in database.")
        return

    print(f"Testing Dice config: {dice_config}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        search_term = dice_config["search_terms"][0]
        location = dice_config["locations"][0]
        url_pattern = dice_config["search_url"]
        
        url = url_pattern.replace("{search_term}", search_term.replace(" ", "%20"))
        url = url.replace("{location}", location.replace(" ", "%20"))
        
        print(f"Navigating to: {url}")
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            print("Page loaded.")
            
            card_sel = dice_config["job_card_selector"]
            print(f"Waiting for selector: {card_sel}")
            await page.wait_for_selector(card_sel, timeout=15000)
            
            cards = await page.locator(card_sel).all()
            print(f"Found {len(cards)} cards.")
            
            for idx, card in enumerate(cards[:3]):
                title_sel = dice_config["title_selector"]
                title_el = card.locator(title_sel).first
                title = await title_el.text_content() if await title_el.count() else "N/A"
                print(f"Card {idx+1}: {title.strip()}")
                
        except Exception as e:
            print(f"Error during test: {e}")
            # Take a screenshot on failure
            await page.screenshot(path="tmp/dice_error.png")
            print("Screenshot saved to tmp/dice_error.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_dice())
