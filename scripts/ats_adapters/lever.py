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
                cats = j.get("categories", {}) or {}
                loc = cats.get("location", "Remote")
                country = j.get("country") or cats.get("country")
                results.append({
                    "title": j.get("text", ""),
                    "company": company_name,
                    "url": j.get("hostedUrl", ""),
                    "location": loc,
                    "country": country.upper() if country else None,
                    "description": j.get("descriptionPlain", "") + "\n" + j.get("additionalPlain", "")
                })
            return results
    except Exception as e:
        return []

