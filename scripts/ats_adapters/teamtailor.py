import urllib.parse

async def fetch_jobs(session, company_name, ats_url):
    # Teamtailor API: https://{slug}.teamtailor.com/en/jobs.json
    parsed = urllib.parse.urlparse(ats_url)
    slug = parsed.netloc.split('.')[0]
    
    if not slug:
        return []
        
    api_url = f"https://{slug}.teamtailor.com/en/jobs.json"
    
    try:
        async with session.get(api_url, timeout=15) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            jobs = data.get("jobs", [])
            results = []
            for j in jobs:
                results.append({
                    "title": j.get("title", ""),
                    "company": company_name,
                    "url": j.get("url", ""),
                    "location": j.get("location", {}).get("city", "Remote"),
                    "description": j.get("body", "")
                })
            return results
    except Exception as e:
        return []
