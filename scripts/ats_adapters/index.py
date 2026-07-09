from scripts.ats_adapters import greenhouse, lever, ashby, workable, smartrecruiters, workday, teamtailor, recruitee, bamboohr, breezy, jobvite, join, personio

ADAPTERS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "workable": workable,
    "smartrecruiters": smartrecruiters,
    "workday": workday,
    "teamtailor": teamtailor,
    "recruitee": recruitee,
    "bamboohr": bamboohr,
    "breezy": breezy,
    "jobvite": jobvite,
    "join": join,
    "personio": personio
}

async def route_company(session, company_name, ats_type, ats_url):
    adapter = ADAPTERS.get(ats_type.lower()) if ats_type else None
    if not adapter:
        return []
        
    try:
        return await adapter.fetch_jobs(session, company_name, ats_url)
    except Exception as e:
        print(f"[!] Error executing adapter for {company_name} ({ats_type}): {e}")
        return []
