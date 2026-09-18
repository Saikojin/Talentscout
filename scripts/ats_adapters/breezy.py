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
                loc_obj = j.get("location", {}) or {}
                loc_name = loc_obj.get("name", "Remote") if isinstance(loc_obj, dict) else str(loc_obj or "Remote")
                country = loc_obj.get("country", {}).get("name") if isinstance(loc_obj, dict) and isinstance(loc_obj.get("country"), dict) else None
                results.append({
                    "title": j.get("name", ""),
                    "company": company_name,
                    "url": j.get("url", ""),
                    "location": loc_name,
                    "country": country.upper() if country else None,
                    "description": j.get("description", "")
                })
            return results
    except Exception as e:
        return []

