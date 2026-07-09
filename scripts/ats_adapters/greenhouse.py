import re
import urllib.parse

async def fetch_jobs(session, company_name, ats_url):
    # Greenhouse slugs can be parsed from Greenhouse URLs: boards.greenhouse.io/slug or boards-api.greenhouse.io/v1/boards/slug/jobs
    # Example URL: https://boards.greenhouse.io/riotgames
    parsed = urllib.parse.urlparse(ats_url)
    path = parsed.path.strip('/')
    slug = path.split('/')[0]
    
    if not slug:
        return []
        
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    
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
                    "url": j.get("absolute_url", ""),
                    "location": j.get("location", {}).get("name", "Remote"),
                    "description": j.get("content", "")
                })
            return results
    except Exception as e:
        return []
