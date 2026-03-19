import os
import json
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
import sys
# Go up one directory to TalentScout root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

import scripts.resume_parser as parser

app = FastAPI(title="TalentScout Resume Parser")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Go up one directory to TalentScout root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")

if not os.path.exists(DASHBOARD_DIR):
    os.makedirs(DASHBOARD_DIR)

app.mount("/dashboard", StaticFiles(directory=DASHBOARD_DIR), name="dashboard")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_path = os.path.join(DASHBOARD_DIR, "resume_scanner.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Resume Scanner UI not found.</h1><p>Ensure dashboard/resume_scanner.html exists.</p>"

@app.post("/api/parse")
async def parse_resume(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
        
    content = await file.read()
    text = parser.extract_text(content, file.filename)
    
    if text.startswith("Error"):
        raise HTTPException(status_code=400, detail=text)
        
    draft_json = parser.draft_skillset(text)
    
    return {
        "text": text,
        "draft_json": draft_json
    }

class SaveRequest(BaseModel):
    skillset: Dict[str, Any]

@app.post("/api/save")
async def save_skillset(req: SaveRequest):
    save_path = os.path.join(BASE_DIR, "base_skillset.json")
    try:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(req.skillset, f, indent=4)
        return {"status": "success", "message": "Saved to base_skillset.json successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from typing import List, Optional, Dict, Any
from scripts.database import get_all_sites, add_site, update_site, delete_site, \
    get_all_search_configs, add_search_config, update_search_config, delete_search_config, \
    get_all_companies, add_company, update_company, delete_company

class SiteConfig(BaseModel):
    name: str
    search_url: str
    job_card_selector: str
    title_selector: str
    company_selector: str
    job_url_selector: str
    
class CompanyConfig(BaseModel):
    name: str
    careers_url: str
    job_card_selector: str
    title_selector: str
    company_selector: str
    job_url_selector: str

class SearchConfig(BaseModel):
    site_id: int
    search_terms: List[str]
    locations: List[str]
    filters: Dict[str, Any]

@app.get("/manage", response_class=HTMLResponse)
async def get_manage():
    index_path = os.path.join(DASHBOARD_DIR, "manage_crawlers.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>manage_crawlers.html not found.</h1>"

@app.get("/api/sites")
async def api_get_sites():
    return get_all_sites()

@app.post("/api/sites")
async def api_add_site(site: SiteConfig):
    sid = add_site(site.name, site.search_url, site.job_card_selector, 
                   site.title_selector, site.company_selector, site.job_url_selector)
    if sid: return {"status": "success", "id": sid}
    raise HTTPException(status_code=500, detail="Failed to add site")

@app.put("/api/sites/{site_id}")
async def api_update_site(site_id: int, site: SiteConfig):
    success = update_site(site_id, site.name, site.search_url, site.job_card_selector, 
                          site.title_selector, site.company_selector, site.job_url_selector)
    if success: return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to update site")

@app.delete("/api/sites/{site_id}")
async def api_delete_site(site_id: int):
    success = delete_site(site_id)
    if success: return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to delete site")

@app.get("/api/configs")
async def api_get_configs():
    return get_all_search_configs()

@app.post("/api/configs")
async def api_add_config(c: SearchConfig):
    cid = add_search_config(c.site_id, c.search_terms, c.locations, c.filters)
    if cid: return {"status": "success", "id": cid}
    raise HTTPException(status_code=500, detail="Failed to add config")

@app.put("/api/configs/{config_id}")
async def api_update_config(config_id: int, c: SearchConfig):
    success = update_search_config(config_id, c.site_id, c.search_terms, c.locations, c.filters)
    if success: return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to update config")

@app.delete("/api/configs/{config_id}")
async def api_delete_config(config_id: int):
    success = delete_search_config(config_id)
    if success: return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to delete config")

@app.get("/api/companies")
async def api_get_companies():
    return get_all_companies()

@app.post("/api/companies")
async def api_add_company(c: CompanyConfig):
    cid = add_company(c.name, c.careers_url, c.job_card_selector, c.title_selector, c.company_selector, c.job_url_selector)
    if cid: return {"status": "success", "id": cid}
    raise HTTPException(status_code=500, detail="Failed to add company")

@app.put("/api/companies/{company_id}")
async def api_update_company(company_id: int, c: CompanyConfig):
    success = update_company(company_id, c.name, c.careers_url, c.job_card_selector, c.title_selector, c.company_selector, c.job_url_selector)
    if success: return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to update company")

@app.delete("/api/companies/{company_id}")
async def api_delete_company(company_id: int):
    success = delete_company(company_id)
    if success: return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to delete company")

if __name__ == "__main__":
    import uvicorn
    # Make sure we're running from the root of the project
    os.chdir(BASE_DIR)
    print("Starting Resume Parser local server on http://localhost:8000")
    uvicorn.run("scripts.resume_server:app", host="localhost", port=8000, reload=True)
