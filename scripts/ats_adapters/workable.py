import urllib.parse

async def fetch_jobs(session, company_name, ats_url):
    # Workable: apply.workable.com/api/v3/accounts/{slug}/jobs
    parsed = urllib.parse.urlparse(ats_url)
    # Host is typically apply.workable.com, path contains company slug
    parts = parsed.path.strip('/').split('/')
    if not parts:
        return []
    slug = parts[0]
    
    api_url = f"https://apply.workable.com/api/v3/accounts/{slug}/jobs"
    headers = {"Content-Type": "application/json"}
    payload = {"limit": 100}
    
    try:
        async with session.post(api_url, json=payload, headers=headers, timeout=15) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            jobs = data.get("results", [])
            
            results = []
            for j in jobs:
                # Workable returns short description. Full description needs another call or we fall back.
                results.append({
                    "title": j.get("title", ""),
                    "company": company_name,
                    "url": f"https://apply.workable.com/{slug}/j/{j.get('shortcode')}/",
                    "location": j.get("location", {}).get("country", "Remote"),
                    "description": j.get("description", "")
                })
            return results
    except Exception as e:
        return []
