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
                results.append({
                    "title": j.get("title", ""),
                    "company": company_name,
                    "url": j.get("jobUrl", ""),
                    "location": j.get("location", "Remote"),
                    "description": j.get("descriptionHtml", "")
                })
            return results
    except Exception as e:
        return []
