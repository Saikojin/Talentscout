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
                results.append({
                    "title": j.get("jobHeader", ""),
                    "company": company_name,
                    "url": f"https://{slug}.bamboohr.com/careers/{j.get('id')}",
                    "location": j.get("location", {}).get("city", "Remote"),
                    "description": j.get("description", "")
                })
            return results
    except Exception as e:
        return []
