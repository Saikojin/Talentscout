import urllib.parse

async def fetch_jobs(session, company_name, ats_url):
    # Recruitee API: https://{slug}.recruitee.com/api/offers
    parsed = urllib.parse.urlparse(ats_url)
    slug = parsed.netloc.split('.')[0]
    
    if not slug:
        return []
        
    api_url = f"https://{slug}.recruitee.com/api/offers"
    
    try:
        async with session.get(api_url, timeout=15) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            jobs = data.get("offers", [])
            results = []
            for j in jobs:
                results.append({
                    "title": j.get("title", ""),
                    "company": company_name,
                    "url": j.get("careers_url", ""),
                    "location": j.get("location", "Remote"),
                    "description": j.get("description", "")
                })
            return results
    except Exception as e:
        return []
