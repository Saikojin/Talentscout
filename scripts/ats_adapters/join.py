import urllib.parse

async def fetch_jobs(session, company_name, ats_url):
    # Join API: https://api.join.com/v1/jobs?companyId={id}
    parsed = urllib.parse.urlparse(ats_url)
    parts = parsed.path.strip('/').split('/')
    if not parts:
        return []
    slug = parts[-1]
    
    api_url = f"https://api.join.com/v1/jobs?companyId={slug}"
    
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
                    "url": j.get("careersUrl", ""),
                    "location": j.get("location", {}).get("city", "Remote"),
                    "description": j.get("description", "")
                })
            return results
    except Exception as e:
        return []
