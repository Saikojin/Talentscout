import urllib.parse

async def fetch_jobs(session, company_name, ats_url):
    # Workday is notoriously dynamic and anti-scraping/API hidden.
    # We implement a generic JSON API fetcher that hits their common Wday tenant board endpoint.
    # Wday path: https://{tenant}.myworkdayjobs.com/wday/cxs/v1/s/page/url
    parsed = urllib.parse.urlparse(ats_url)
    tenant_host = parsed.netloc
    
    if "myworkdayjobs.com" not in tenant_host:
        return []
        
    # Get tenant name
    tenant = tenant_host.split('.')[0]
    
    # Path extraction
    path_parts = parsed.path.strip('/').split('/')
    if not path_parts:
        return []
    board_name = path_parts[0] # e.g. "RiotGamesCareers"
    
    api_url = f"https://{tenant_host}/wday/cxs/v1/{tenant}/jobs"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "appliedFacets": {},
        "limit": 20,
        "offset": 0,
        "searchText": ""
    }
    
    try:
        async with session.post(api_url, json=payload, headers=headers, timeout=15) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            jobs = data.get("jobPostings", [])
            results = []
            for j in jobs:
                results.append({
                    "title": j.get("title", ""),
                    "company": company_name,
                    "url": f"https://{tenant_host}{j.get('externalPath')}",
                    "location": j.get("locationsText", "Remote"),
                    "description": "" # Description usually fetched separately; fallback handles it
                })
            return results
    except Exception as e:
        return []
