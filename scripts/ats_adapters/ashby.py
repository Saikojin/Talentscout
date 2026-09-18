import re
import urllib.parse

async def fetch_jobs(session, company_name, ats_url):
    # Ashby board api: https://jobs.ashbyhq.com/api/non-user-facing/posting-board/slug
    parsed = urllib.parse.urlparse(ats_url)
    path = parsed.path.strip('/')
    slug = path.split('/')[0]
    
    if not slug:
        return []
        
    api_url = f"https://jobs.ashbyhq.com/api/non-user-facing/posting-board/{slug}"
    
    try:
        async with session.get(api_url, timeout=15) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            jobs = data.get("jobs", [])
            
            results = []
            for j in jobs:
                loc = j.get("location", "Remote")
                addr = j.get("address", {}) or {}
                country = addr.get("country") or j.get("country")
                results.append({
                    "title": j.get("title", ""),
                    "company": company_name,
                    "url": j.get("jobUrl", ""),
                    "location": loc,
                    "country": country.upper() if country else None,
                    "description": j.get("descriptionHtml", "")
                })
            return results
    except Exception as e:
        return []

