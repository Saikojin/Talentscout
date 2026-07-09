import urllib.parse

async def fetch_jobs(session, company_name, ats_url):
    # Personio API: XML-based typically, but some endpoints return JSON or we fall back.
    # To keep it reliable and simple (Personio blocks aggressive queries), we query its XML feed.
    # Feed: https://{slug}.jobs.personio.de/xml
    parsed = urllib.parse.urlparse(ats_url)
    slug = parsed.netloc.split('.')[0]
    
    if not slug:
        return []
        
    api_url = f"https://{slug}.jobs.personio.de/xml"
    
    try:
        async with session.get(api_url, timeout=15) as resp:
            if resp.status != 200:
                return []
            xml_text = await resp.text()
            
            # Simple manual XML parsing to avoid external dependencies
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_text)
            
            results = []
            for position in root.findall('.//position'):
                title = position.find('name')
                job_id = position.find('id')
                office = position.find('office')
                description = position.find('jobDescription')
                
                title_text = title.text if title is not None else ""
                url = f"https://{slug}.jobs.personio.de/job/{job_id.text}" if job_id is not None else ats_url
                loc = office.text if office is not None else "Remote"
                desc = description.text if description is not None else ""
                
                results.append({
                    "title": title_text,
                    "company": company_name,
                    "url": url,
                    "location": loc,
                    "description": desc
                })
            return results
    except Exception as e:
        return []
