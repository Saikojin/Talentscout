import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

LOGS_DIR = "logs"

async def highlight_and_screenshot(page, selectors, name):
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
        
    out_path = os.path.join(LOGS_DIR, f"verification_{name}.png")
    print(f"[*] Visualizing selectors for {name}...")
    
    # Colors for different selector types
    colors = {
        "job_card_selector": "red",
        "title_selector": "blue",
        "company_selector": "green",
        "job_url_selector": "yellow"
    }
    
    try:
        for key, selector in selectors.items():
            if not selector: continue
            color = colors.get(key, "magenta")
            print(f"  [+] Highlighting '{key}': {selector} ({color})")
            
            await page.evaluate('''({sel, col}) => {
                const els = document.querySelectorAll(sel);
                els.forEach(el => {
                    el.style.border = `4px solid ${col}`;
                    el.style.boxSizing = 'border-box';
                    el.style.position = 'relative';
                    el.style.zIndex = '9999';
                    
                    // Add a small label
                    const label = document.createElement('div');
                    label.textContent = sel;
                    label.style.position = 'absolute';
                    label.style.top = '0';
                    label.style.left = '0';
                    label.style.background = col;
                    label.style.color = 'white';
                    label.style.fontSize = '10px';
                    label.style.padding = '2px';
                    label.style.zIndex = '10000';
                    el.appendChild(label);
                });
            }''', {"sel": selector, "col": color})
        
        await page.wait_for_timeout(1000) # Wait for render
        await page.screenshot(path=out_path, full_page=False)
        print(f"  [+] Screenshot saved to {out_path}")
        
    except Exception as e:
        print(f"  [!] Failed to highlight/screenshot: {e}")

async def verify_site(url, site_name, selectors):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 1080}
        )
        page = await context.new_page()
        
        print(f"[*] Navigating to {url}...")
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(5000) # Extra wait for dynamic content
            
            # Scroll a bit
            await page.mouse.wheel(0, 1000)
            await page.wait_for_timeout(2000)
            
            await highlight_and_screenshot(page, selectors, site_name)
        except Exception as e:
            print(f"  [!] Navigation failed: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/verify_selectors.py <url> <site_name> '<json_selectors>'")
        sys.exit(1)
        
    url = sys.argv[1]
    name = sys.argv[2]
    try:
        selectors = json.loads(sys.argv[3])
    except json.JSONDecodeError:
        # If not valid JSON, assume it's a single selector for job cards (backward compat or quick test)
        selectors = {"job_card_selector": sys.argv[3]}
        
    asyncio.run(verify_site(url, name, selectors))
