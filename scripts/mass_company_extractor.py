import asyncio
import os
import sys
import json
import sqlite3
from urllib.parse import urlparse, urljoin, quote_plus, parse_qs
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.database import add_company, get_all_companies

async def extract_sp500(browser):
    print("\n[====== S&P 500 EXTRACTION ======]")
    context = await browser.new_context()
    page = await context.new_page()
    
    # 1. Get the list
    print("[*] Loading S&P 500 Wikipedia list...")
    await page.goto("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", wait_until="domcontentloaded")
    
    html = await page.content()
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', {'id': 'constituents'})
    rows = table.find_all('tr')[1:] # Skip header
    
    companies = []
    for row in rows:
        cols = row.find_all(['td', 'th'])
        if len(cols) >= 2:
            a_tag = cols[1].find('a') # The company name and link to its wiki
            if a_tag and a_tag.get('href'):
                name = a_tag.text.strip()
                wiki_url = urljoin("https://en.wikipedia.org", a_tag.get('href'))
                companies.append({"name": name, "wiki_url": wiki_url})
                
    print(f"[*] Found {len(companies)} S&P 500 companies. Resolving official websites...")
    
    # Check existing domains to avoid re-fetching
    existing_companies = {c['name'].lower() for c in get_all_companies()}
    
    added_count = 0
    # Process them (Batching or sequential)
    for idx, comp in enumerate(companies):
        cname = comp['name']
        if cname.lower() in existing_companies:
            print(f"  [{idx+1}/{len(companies)}] Skipping {cname} (Already in DB)")
            continue
            
        print(f"  [{idx+1}/{len(companies)}] Scraping Wiki for {cname}...")
        try:
            await page.goto(comp['wiki_url'], wait_until="domcontentloaded", timeout=15000)
            c_html = await page.content()
            c_soup = BeautifulSoup(c_html, 'html.parser')
            
            # Find infobox
            infobox = c_soup.find('table', {'class': 'infobox'})
            if not infobox:
                print(f"    [!] No infobox found for {cname}")
                continue
                
            website_th = infobox.find(lambda tag: tag.name == 'th' and 'Website' in tag.text)
            if website_th:
                website_td = website_th.find_next_sibling('td')
                if website_td:
                    url_a = website_td.find('a', href=True)
                    if url_a:
                        website_url = url_a['href']
                        if not website_url.startswith('http'):
                            website_url = 'https://' + website_url.lstrip('/')
                            
                        # Format careers URL
                        base = website_url.rstrip('/')
                        careers_url = f"{base}/careers"
                        
                        # Add to DB
                        cid = add_company(cname, careers_url, "", "", "", "")
                        if cid:
                            print(f"    [+] Added {cname} -> {careers_url}")
                            added_count += 1
                        continue
                        
            print(f"    [!] Could not parse website for {cname}")
        except Exception as e:
            print(f"    [!] Error processing {cname}: {e}")
            
    await context.close()
    print(f"[*] Finished S&P 500 extraction. Added {added_count} new companies.")

import requests
import time

async def extract_clutch_us(browser):
    print("\n[====== CLUTCH.CO US DEVELOPERS EXTRACTION ======]")
    print("\n*** OFFLINE WORKFLOW INITIATED due to Cloudflare ***")
    print("Because Clutch.co's Cloudflare strictly blocks automated browsers, we must use an offline workflow.")
    print("1. Open your normal Google Chrome browser.")
    print("2. Navigate to https://clutch.co/us/developers")
    print("3. Right click the page -> 'Save As' -> save it as 'clutch.html' inside the TalentScout folder.")
    print("   (You can save multiple pages as clutch_1.html, clutch_2.html, etc. and merge them, or just save one).")
    input("\nPlease press ENTER once you have saved at least 'clutch.html' in the TalentScout directory: ")
    
    # Find all saved clutch html files
    clutch_files = [f for f in os.listdir(".") if f.startswith("clutch") and f.endswith(".html") and "debug" not in f]
    
    if not clutch_files:
        print("[!] Could not find any files named clutch.html in the current directory. Aborting.")
        return
        
    existing_companies = {c['name'].lower() for c in get_all_companies()}
    added_count = 0
    
    for filename in clutch_files:
        print(f"\n[*] Parsing offline file: {filename}...")
        try:
            with open(filename, "r", encoding="utf-8") as f:
                c_html = f.read()
                
            soup = BeautifulSoup(c_html, 'html.parser')
            # Offline HTML format often uses div or article instead of li
            providers = soup.find_all(class_='provider-row')
            if not providers:
                print(f"[!] No providers found in {filename}.")
                continue
                
            print(f"[*] Found {len(providers)} providers in {filename}. Resolving URLs via DuckDuckGo...")
            
            for prov in providers:
                name_elem = prov.find('h3', class_='provider__title')
                if not name_elem: continue
                name_a = name_elem.find('a')
                if not name_a: continue
                cname = name_a.text.strip()
                
                if cname.lower() in existing_companies:
                    continue
                
                # Find the 'Visit Website' raw URL embedded in the offline HTML
                website_elem = prov.find('a', class_='website-link__item')
                found_url = None
                
                if website_elem and website_elem.get('data-link'):
                    # The offline HTML encodes the true URL in the data-link attribute under the 'u' query parameter
                    raw_data_link = website_elem.get('data-link')
                    parsed_link = urlparse(raw_data_link)
                    query_params = parse_qs(parsed_link.query)
                    
                    if 'u' in query_params:
                        raw_website = query_params['u'][0]
                        # Clean it
                        parsed_website = urlparse(raw_website)
                        found_url = f"{parsed_website.scheme}://{parsed_website.netloc}"
                
                if found_url:
                    found_url = found_url.rstrip('/') + '/careers'
                    cid = add_company(cname, found_url, "", "", "", "")
                    if cid:
                        print(f"      [+] Added Agency: {cname} -> {found_url}")
                        added_count += 1
                        existing_companies.add(cname.lower())
                else:
                    print(f"      [-] Could not resolve URL for {cname}")
                    
        except Exception as e:
            print(f"[!] Error parsing {filename}: {e}")
            
    print(f"\n[*] Finished Clutch offline extraction. Added {added_count} new agencies.")

async def main():
    print("Welcome to the Mass Company Extractor")
    print("1. Extract S&P 500 (Wikipedia)")
    print("2. Extract US Agencies (Clutch.co)")
    print("3. Extract BOTH")
    
    choice = input("Select an option (1-3): ").strip()
    
    async with async_playwright() as p:
        # Launch non-headless because Clutch WILL trigger Cloudflare and duckduckgo sometimes triggers Captcha
        browser = await p.chromium.launch(headless=False)
        
        if choice in ['1', '3']:
            await extract_sp500(browser)
            
        if choice in ['2', '3']:
            await extract_clutch_us(browser)
            
        await browser.close()
        
    print("\n[*] All extraction processes completed! You can now run `auto_scour.py` to search these companies.")

if __name__ == "__main__":
    asyncio.run(main())
