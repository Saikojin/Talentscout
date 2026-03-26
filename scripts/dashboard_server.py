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

if __name__ == "__main__":
    import uvicorn
    os.chdir(BASE_DIR)
    print("Starting Dashboard Server on http://localhost:8001")
    uvicorn.run("scripts.dashboard_server:app", host="localhost", port=8001, reload=True)
