import urllib.parse

async def fetch_jobs(session, company_name, ats_url):
    # BambooHR API: https://{slug}.bamboohr.com/careers/list
    parsed = urllib.parse.urlparse(ats_url)
    slug = parsed.netloc.split('.')[0]
    
    if not slug:
        return []
        
    api_url = f"https://{slug}.bamboohr.com/careers/list"
    
    try:
        async with session.get(api_url, timeout=15) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            # BambooHR returns a list of jobs
            results = []
            for j in data:
                loc_obj = j.get("location", {}) or {}
                city = loc_obj.get("city", "")
                state = loc_obj.get("state", "")
                country = loc_obj.get("country", "")
                loc_parts = [p for p in [city, state, country] if p]
                loc_str = ", ".join(loc_parts) or "Remote"
                
                results.append({
                    "title": j.get("jobHeader", ""),
                    "company": company_name,
                    "url": f"https://{slug}.bamboohr.com/careers/{j.get('id')}",
                    "location": loc_str,
                    "country": country.upper() if country else None,
                    "description": j.get("description", "")
                })
            return results
    except Exception as e:
        return []

