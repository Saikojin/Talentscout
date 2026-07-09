import urllib.parse

async def fetch_jobs(session, company_name, ats_url):
    # Breezy API: https://{slug}.breezy.hr/json
    parsed = urllib.parse.urlparse(ats_url)
    slug = parsed.netloc.split('.')[0]
    
    if not slug:
        return []
        
    api_url = f"https://{slug}.breezy.hr/json"
    
    try:
        async with session.get(api_url, timeout=15) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            results = []
            for j in data:
                results.append({
                    "title": j.get("name", ""),
                    "company": company_name,
                    "url": j.get("url", ""),
                    "location": j.get("location", {}).get("name", "Remote"),
                    "description": j.get("description", "")
                })
            return results
    except Exception as e:
        return []
