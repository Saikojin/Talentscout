import urllib.parse

async def fetch_jobs(session, company_name, ats_url):
    # SmartRecruiters API: api.smartrecruiters.com/v1/companies/{slug}/postings
    parsed = urllib.parse.urlparse(ats_url)
    parts = parsed.path.strip('/').split('/')
    if not parts:
        return []
    slug = parts[0]
    
    api_url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
    
    try:
        async with session.get(api_url, timeout=15) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            jobs = data.get("content", [])
            
            results = []
            for j in jobs:
                loc_obj = j.get("location", {}) or {}
                city = loc_obj.get("city", "")
                region = loc_obj.get("region", "")
                country = loc_obj.get("country", "")
                is_remote = loc_obj.get("remote", False)
                
                loc_parts = [p for p in [city, region, country] if p]
                loc_str = ", ".join(loc_parts)
                if is_remote:
                    loc_str = f"Remote, {loc_str}" if loc_str else "Remote"
                elif not loc_str:
                    loc_str = "Remote"
                    
                results.append({
                    "title": j.get("name", ""),
                    "company": company_name,
                    "url": f"https://jobs.smartrecruiters.com/{slug}/{j.get('id')}",
                    "location": loc_str,
                    "country": country.upper() if country else None,
                    "description": "" # Needs secondary fetch or fallback
                })
            return results
    except Exception as e:
        return []

