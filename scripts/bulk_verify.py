import json
import asyncio
import subprocess
import os

SELECTORS_FILE = "site_selectors.json"

async def run_verify(site_name, config):
    url = config.get("search_url")
    if not url:
        print(f"[!] No search_url for {site_name}")
        return
        
    # Replace placeholders
    url = url.replace("{search_term}", "Senior+QA+Engineer").replace("{location}", "Seattle")
    
    selectors = {
        "job_card_selector": config.get("job_card_selector"),
        "title_selector": config.get("title_selector"),
        "company_selector": config.get("company_selector"),
        "job_url_selector": config.get("job_url_selector")
    }
    
    selectors_json = json.dumps(selectors)
    
    print(f"[*] Verifying {site_name}...")
    # Use subprocess to run the verification script to keep them isolated
    process = await asyncio.create_subprocess_exec(
        'python', 'scripts/verify_selectors.py', url, site_name, selectors_json,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if stdout:
        print(stdout.decode())
    if stderr:
        print(stderr.decode())

async def main():
    if not os.path.exists(SELECTORS_FILE):
        print(f"[!] {SELECTORS_FILE} not found")
        return
        
    with open(SELECTORS_FILE, "r") as f:
        data = json.load(f)
        
    tasks = []
    for site_name, config in data.items():
        tasks.append(run_verify(site_name, config))
        
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
