import re
import urllib.parse

async def fetch_jobs(session, company_name, ats_url):
    # Lever postings api: https://api.lever.co/v0/postings/slug
    parsed = urllib.parse.urlparse(ats_url)
    path = parsed.path.strip('/')
    slug = path.split('/')[0]
    
    if not slug:
        return []
        
    api_url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    
    try:
        async with session.get(api_url, timeout=15) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            
            results = []
            for j in data:
                results.append({
                    "title": j.get("text", ""),
                    "company": company_name,
                    "url": j.get("hostedUrl", ""),
                    "location": j.get("categories", {}).get("location", "Remote"),
                    "description": j.get("descriptionPlain", "") + "\n" + j.get("additionalPlain", "")
                })
            return results
    except Exception as e:
        return []
