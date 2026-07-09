import urllib.parse

async def fetch_jobs(session, company_name, ats_url):
    # Jobvite API: https://jobs.jobvite.com/api/job?c={id}&sc=0
    parsed = urllib.parse.urlparse(ats_url)
    # Extract query param c
    query = urllib.parse.parse_qs(parsed.query)
    c_id = query.get('c', [None])[0]
    
    if not c_id:
        # Check path: jobs.jobvite.com/slug
        parts = parsed.path.strip('/').split('/')
        if parts:
            c_id = parts[0]
            
    if not c_id:
        return []
        
    api_url = f"https://jobs.jobvite.com/api/job?c={c_id}&sc=0"
    
    try:
        async with session.get(api_url, timeout=15) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            results = []
            for j in data:
                results.append({
                    "title": j.get("title", ""),
                    "company": company_name,
                    "url": j.get("detail-url", ""),
                    "location": j.get("location", "Remote"),
                    "description": j.get("description", "")
                })
            return results
    except Exception as e:
        return []
