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

if __name__ == "__main__":
    import uvicorn
    # Make sure we're running from the root of the project
    os.chdir(BASE_DIR)
    print("Starting Resume Parser local server on http://localhost:8000")
    uvicorn.run("scripts.resume_server:app", host="localhost", port=8000, reload=True)
