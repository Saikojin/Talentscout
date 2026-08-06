import os
import sys
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

import scripts.database as db

import scripts.profile as profile_mgr
import scripts.scorer as scorer

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

if __name__ == "__main__":
    import uvicorn
    os.chdir(BASE_DIR)
    port = 8088
    print(f"Starting Dashboard & Profile Server on http://localhost:{port}")
    uvicorn.run("scripts.dashboard_server:app", host="localhost", port=port, reload=True)
