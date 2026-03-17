import asyncio
import json
import os
from collections import Counter
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

CONFIG_FILE = "site_configs.json"
LOGS_DIR = "logs"

def load_configs():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

try:
    from scripts.cleanup import clean_logs
except ImportError:
    def clean_logs(d): pass

def save_configs(configs):
    with open(CONFIG_FILE, "w") as f:
        json.dump(configs, f, indent=2)

def extract_domain(url):
    parsed_uri = urlparse(url)
    domain = '{uri.netloc}'.format(uri=parsed_uri)
    return domain.replace('www.', '')

def get_class_selector(element):
    classes = element.get('class', [])
    if classes:
        return "." + ".".join(classes)
    return None

async def highlight_and_screenshot(page, selector, name, color="red"):
    out_path = os.path.join(LOGS_DIR, f"highlight_{name}.png")
    print(f"  [+] Injecting {color} border for '{selector}'...")
    
    # Store original styles to revert later if needed (simple version: just add a class/style)
    try:
        await page.evaluate(f'''() => {{
            const els = document.querySelectorAll('{selector}');
            els.forEach(el => {{
                el.style.border = '4px solid {color}';
                el.style.boxSizing = 'border-box';
                el.style.zIndex = '9999';
            }});
        }}''')
        
        await page.wait_for_timeout(500) # Wait for render
        await page.screenshot(path=out_path, full_page=False)
        print(f"  [+] Screenshot saved to {out_path}")
        
        # Revert
        await page.evaluate(f'''() => {{
            const els = document.querySelectorAll('{selector}');
            els.forEach(el => {{
                el.style.border = '';
            }});
        }}''')
    except Exception as e:
        print(f"  [!] Failed to highlight/screenshot: {e}")

async def interactive_selection(page, items_list, item_name, color="red"):
    if not items_list: return ""
    
    print(f"\n--- Select {item_name} ---")
    for i, (cls, count) in enumerate(items_list):
        print(f"  [{i+1}] {cls} ({count} occurrences)")
    print(f"  [0] Skip / Enter manually")
    
    while True:
        try:
            choice = input(f"Enter the number to preview (or 0 to skip): ")
            if choice == "" or choice == "0":
                manual = input(f"Enter manual selector for {item_name} (or enter to skip): ")
                return manual.strip()
                
            idx = int(choice) - 1
            if 0 <= idx < len(items_list):
                selected_cls = items_list[idx][0]
                await highlight_and_screenshot(page, selected_cls, item_name.replace(" ", "_").lower(), color)
                
                confirm = input(f"Does logs/highlight_{item_name.replace(' ', '_').lower()}.png look correct? (y/n/manual): ").lower()
                if confirm == 'y':
                    return selected_cls
                elif confirm == 'manual':
                    return input(f"Enter manual selector: ").strip()
                # Otherwise loop again
            else:
                print("Invalid choice.")
        except ValueError:
            print("Please enter a number.")

async def learn_site(url, site_name):
    domain = extract_domain(url)
    print(f"[*] Starting visual learning process for {site_name} ({domain})")
    print(f"[*] URL: {url}")
    
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
        
    # Clean old screenshots before starting
    clean_logs(LOGS_DIR)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) # Keep headless, rely on screenshots
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 1080}
        )
        page = await context.new_page()
        
        print("[*] Loading page and waiting for network idle...")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)
        
        # Scroll to load images/lazy elements
        await page.mouse.wheel(0, 2000)
        await page.wait_for_timeout(2000)
        
        html_content = await page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        print("[*] Analyzing DOM structures...")
        
        # Containers (divs that appear multiple times, likely cards)
        divs = soup.find_all('div')
        div_classes = [get_class_selector(d) for d in divs if get_class_selector(d)]
        container_candidates = [(cls, count) for cls, count in Counter(div_classes).most_common(15) if 5 < count < 50]
        
        # Titles (h2/h3)
        headers = soup.find_all(['h2', 'h3'])
        header_classes = [get_class_selector(h) for h in headers if get_class_selector(h)]
        title_candidates = [(cls, count) for cls, count in Counter(header_classes).most_common(10)]
        
        # URLs (a tags)
        links = soup.find_all('a', href=True)
        link_classes = []
        for a in links:
            if a.text.strip():
                cls = get_class_selector(a)
                if cls: link_classes.append(cls)
        url_candidates = [(cls, count) for cls, count in Counter(link_classes).most_common(15) if count > 5]
        
        # Interactive UI
        print("\n*** Visual Selector Configuration ***")
        
        card_sel = await interactive_selection(page, container_candidates, "Job Card Container", "red")
        title_sel = await interactive_selection(page, title_candidates, "Job Title", "blue")
        url_sel = await interactive_selection(page, url_candidates, "Job URL", "green")
        
        company_sel = input("\n[Optional] Enter company selector if known (or leave blank to use fallback): ").strip()
        
        if card_sel or title_sel or url_sel:
            configs = load_configs()
            configs[site_name] = {
                "domain": domain,
                "job_card_selector": card_sel,
                "title_selector": title_sel,
                "company_selector": company_sel,
                "job_url_selector": url_sel,
            }
            save_configs(configs)
            print(f"\n[*] Saved structured config for {site_name} to {CONFIG_FILE}")
        else:
            print("\n[!] No selectors saved.")
            
        await browser.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python scripts/crawler_learner.py <url> <SiteName>")
        sys.exit(1)
        
    asyncio.run(learn_site(sys.argv[1], sys.argv[2]))
