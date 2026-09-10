import os
import sys
import json
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

import scripts.database as db
import scripts.profile as profile_mgr
import scripts.scorer as scorer
import scripts.resume_parser as parser

app = FastAPI(title="TalentScout Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DASHBOARD_DIR = BASE_DIR

app.mount("/static", StaticFiles(directory=DASHBOARD_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    dashboard_path = os.path.join(DASHBOARD_DIR, "dashboard.html")
    if os.path.exists(dashboard_path):
        with open(dashboard_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Dashboard UI not found.</h1>"

@app.get("/profiles", response_class=HTMLResponse)
async def get_profile_editor_page():
    page_path = os.path.join(DASHBOARD_DIR, "dashboard", "profile_editor.html")
    if os.path.exists(page_path):
        with open(page_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Profile Editor UI not found.</h1>"

@app.get("/scanner", response_class=HTMLResponse)
async def get_scanner_page():
    page_path = os.path.join(DASHBOARD_DIR, "dashboard", "resume_scanner.html")
    if os.path.exists(page_path):
        with open(page_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Resume Scanner UI not found.</h1>"

@app.get("/manage", response_class=HTMLResponse)
async def get_manage_page():
    page_path = os.path.join(DASHBOARD_DIR, "dashboard", "manage_crawlers.html")
    if os.path.exists(page_path):
        with open(page_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Manage Crawlers UI not found.</h1>"

@app.post("/api/parse")
async def parse_resume(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    content = await file.read()
    text = parser.extract_text(content, file.filename)
    if text.startswith("Error"):
        raise HTTPException(status_code=400, detail=text)
    draft_json = parser.draft_skillset(text)
    return {"text": text, "draft_json": draft_json}

class SkillsetSaveReq(BaseModel):
    skillset: Dict[str, Any]

@app.post("/api/save")
async def save_skillset(req: SkillsetSaveReq):
    save_path = os.path.join(BASE_DIR, "base_skillset.json")
    try:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(req.skillset, f, indent=4)
        return {"status": "success", "message": "Saved to base_skillset.json successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    website: Optional[str] = None
    ats_type: Optional[str] = None
    ats_url: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    industry_category: Optional[str] = None
    countries: Optional[List[str]] = None

class SearchConfig(BaseModel):
    site_id: int
    search_terms: List[str]
    locations: List[str]
    filters: Dict[str, Any]

@app.get("/api/sites")
async def api_get_sites():
    return db.get_all_sites()

@app.post("/api/sites")
async def api_add_site(site: SiteConfig):
    sid = db.add_site(site.name, site.search_url, site.job_card_selector, 
                      site.title_selector, site.company_selector, site.job_url_selector)
    if sid: return {"status": "success", "id": sid}
    raise HTTPException(status_code=500, detail="Failed to add site")

@app.put("/api/sites/{site_id}")
async def api_update_site(site_id: int, site: SiteConfig):
    success = db.update_site(site_id, site.name, site.search_url, site.job_card_selector, 
                             site.title_selector, site.company_selector, site.job_url_selector)
    if success: return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to update site")

@app.delete("/api/sites/{site_id}")
async def api_delete_site(site_id: int):
    success = db.delete_site(site_id)
    if success: return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to delete site")

@app.get("/api/configs")
async def api_get_configs():
    return db.get_all_search_configs()

@app.post("/api/configs")
async def api_add_config(c: SearchConfig):
    cid = db.add_search_config(c.site_id, c.search_terms, c.locations, c.filters)
    if cid: return {"status": "success", "id": cid}
    raise HTTPException(status_code=500, detail="Failed to add config")

@app.put("/api/configs/{config_id}")
async def api_update_config(config_id: int, c: SearchConfig):
    success = db.update_search_config(config_id, c.site_id, c.search_terms, c.locations, c.filters)
    if success: return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to update config")

@app.delete("/api/configs/{config_id}")
async def api_delete_config(config_id: int):
    success = db.delete_search_config(config_id)
    if success: return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to delete config")

@app.get("/api/companies")
async def api_get_companies():
    return db.get_all_companies()

@app.post("/api/companies")
async def api_add_company(c: CompanyConfig):
    cid = db.add_company(
        c.name, c.careers_url, c.job_card_selector, c.title_selector, c.company_selector, c.job_url_selector,
        c.website, c.ats_type, c.ats_url, c.tech_stack, c.industry_category, c.countries
    )
    if cid: return {"status": "success", "id": cid}
    raise HTTPException(status_code=500, detail="Failed to add company")

@app.put("/api/companies/{company_id}")
async def api_update_company(company_id: int, c: CompanyConfig):
    success = db.update_company(
        company_id, c.name, c.careers_url, c.job_card_selector, c.title_selector, c.company_selector, c.job_url_selector,
        c.website, c.ats_type, c.ats_url, c.tech_stack, c.industry_category, c.countries
    )
    if success: return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to update company")

@app.delete("/api/companies/{company_id}")
async def api_delete_company(company_id: int):
    success = db.delete_company(company_id)
    if success: return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to delete company")

@app.get("/api/jobs")
async def get_jobs():
    jobs = db.get_new_jobs()
    for job in jobs:
        # Parse skills back to list if it's a JSON string
        if job.get("missing_skills"):
            try:
                job["missing_skills"] = json.loads(job["missing_skills"])
            except json.JSONDecodeError:
                job["missing_skills"] = []
        if job.get("matched_skills"):
            try:
                job["matched_skills"] = json.loads(job["matched_skills"])
            except json.JSONDecodeError:
                job["matched_skills"] = []
    return jobs

class StatusUpdate(BaseModel):
    status: str

@app.put("/api/jobs/{job_id}/status")
async def update_status(job_id: int, req: StatusUpdate):
    success = db.update_job_status(job_id, req.status)
    if success:
        return {"status": "success", "message": f"Job {job_id} updated to {req.status}"}
    raise HTTPException(status_code=400, detail="Failed to update job status. Invalid status or job ID.")

class ThresholdRequest(BaseModel):
    threshold: int

@app.post("/api/jobs/reject_by_score")
async def reject_by_score(req: ThresholdRequest):
    count = db.reject_jobs_below_score(req.threshold)
    return {"status": "success", "message": f"Rejected {count} jobs", "count": count}

# --- Profile Endpoints ---

@app.get("/api/profiles")
async def list_profiles():
    return profile_mgr.list_profiles()

@app.get("/api/profiles/active")
async def get_active_profile():
    return profile_mgr.get_active_profile()

@app.get("/api/profiles/{profile_id}")
async def get_profile(profile_id: int):
    p = profile_mgr.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p

class ProfileCreateReq(BaseModel):
    name: str
    description: str = ""
    config: dict

@app.post("/api/profiles")
async def create_profile(req: ProfileCreateReq):
    try:
        pid = profile_mgr.create_profile(req.name, req.description, req.config)
        return {"status": "success", "profile_id": pid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/profiles/{profile_id}")
async def update_profile(profile_id: int, req: ProfileCreateReq):
    success = profile_mgr.update_profile(profile_id, req.name, req.description, req.config)
    if success:
        return {"status": "success"}
    raise HTTPException(status_code=400, detail="Failed to update profile")

@app.post("/api/profiles/{profile_id}/activate")
async def activate_profile(profile_id: int):
    success = profile_mgr.activate_profile(profile_id)
    if success:
        return {"status": "success", "message": f"Activated profile {profile_id}"}
    raise HTTPException(status_code=400, detail="Profile not found or activation failed")

@app.delete("/api/profiles/{profile_id}")
async def delete_profile(profile_id: int):
    try:
        success = profile_mgr.delete_profile(profile_id)
        if success:
            return {"status": "success"}
        raise HTTPException(status_code=400, detail="Could not delete profile")
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

@app.post("/api/profiles/{profile_id}/rescore")
async def rescore_jobs(profile_id: int):
    """Re-score all jobs in DB using specified profile. Does NOT alter status per user requirement."""
    p_data = profile_mgr.get_profile(profile_id)
    if not p_data:
        raise HTTPException(status_code=404, detail="Profile not found")

    conn = db.create_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection error")

    count = 0
    try:
        conn.row_factory = db.sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, missing_skills, matched_skills FROM jobs")
        rows = cursor.fetchall()
        
        for r in rows:
            # Construct dummy JD text from title + skills for re-scoring calculation
            skills_text = ""
            if r["matched_skills"]:
                try: skills_text += " " + " ".join(json.loads(r["matched_skills"]))
                except: pass
            if r["missing_skills"]:
                try: skills_text += " " + " ".join(json.loads(r["missing_skills"]))
                except: pass
            
            fake_jd = f"{r['title']}{skills_text}"
            res = scorer.score_job(fake_jd, title=r['title'], profile_data=p_data)
            
            cursor.execute("""
                UPDATE jobs SET score = ?, score_profile_id = ? WHERE id = ?
            """, (res["score"], profile_id, r["id"]))
            count += 1
            
        conn.commit()
    finally:
        conn.close()
        
    return {"status": "success", "rescored_count": count}

# --- LLM & Resume Tailoring Endpoints ---
import scripts.tailor_engine as tailor_engine

@app.get("/api/llm/status")
async def get_llm_status():
    """Returns local LLM server status and list of available models."""
    return tailor_engine.check_llm_status()

class LLMStartReq(BaseModel):
    model: Optional[str] = None

@app.post("/api/llm/start")
async def start_llm(req: LLMStartReq):
    """Start local LLMWorkbench backend server."""
    res = tailor_engine.start_llm_server(req.model)
    return res

@app.post("/api/llm/stop")
async def stop_llm():
    """Stop local LLMWorkbench backend server."""
    return tailor_engine.stop_llm_server()

class LLMTestReq(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    custom_endpoint: Optional[str] = None

@app.post("/api/profiles/{profile_id}/test_llm")
async def test_profile_llm(profile_id: int, req: Optional[LLMTestReq] = None):
    """Test ping connection and API key validity for a given profile provider."""
    p = profile_mgr.get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    p_cfg = p.get("config", {})
    llm_cfg = p_cfg.get("llm", {})
    
    provider = (req.provider if (req and req.provider) else llm_cfg.get("provider", "local")).lower()
    model = req.model if (req and req.model) else llm_cfg.get("model_name")
    custom_endpoint = req.custom_endpoint if (req and req.custom_endpoint) else llm_cfg.get("custom_endpoint", "")
    
    # Resolve API key from request, profile, or environment
    api_key = req.api_key if (req and req.api_key) else llm_cfg.get("api_keys", {}).get(provider, "")
    
    result = tailor_engine.test_provider_connection(
        provider=provider,
        model=model,
        api_key=api_key,
        custom_endpoint=custom_endpoint
    )
    return result

class TailorRequest(BaseModel):
    model: Optional[str] = None
    provider: Optional[str] = None

@app.post("/api/jobs/{job_id}/tailor")
async def generate_tailored_resume(job_id: int, req: Optional[TailorRequest] = None):
    """Generate tailored resume and cover letter for a given job."""
    model_name = req.model if req else None
    provider = req.provider if req else None
    try:
        result = tailor_engine.tailor_for_job(job_id, model_name=model_name, provider=provider)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs/{job_id}/tailor")
async def get_tailored_resume(job_id: int):
    """Check if tailored resume & cover letter already exist for a job."""
    existing = tailor_engine.get_existing_tailored_package(job_id)
    if not existing:
        return {"exists": False}
    return existing

if __name__ == "__main__":
    import uvicorn
    import argparse
    parser = argparse.ArgumentParser(description="TalentScout Dashboard Server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("DASHBOARD_PORT", os.environ.get("PORT", 8088))), help="Port to run server on")
    parser.add_argument("--host", type=str, default="localhost", help="Host to bind to")
    args = parser.parse_args()

    os.chdir(BASE_DIR)
    port = args.port
    print(f"Starting TalentScout Unified Dashboard Server on http://{args.host}:{port}")
    uvicorn.run("scripts.dashboard_server:app", host=args.host, port=port, reload=True)

