import os
import sys
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

import scripts.tailor_engine as tailor_engine
import scripts.database as db

def test_tailor_engine():
    print("=" * 60)
    print("Testing Tailor Engine & Local LLM Integration")
    print("=" * 60)

    # 1. Test LLM status check & model discovery
    status = tailor_engine.check_llm_status()
    print(f"[1] LLM Status: {status['backend']} (Online: {status['online']}, Active: {status['active_model']})")
    print(f"    Available Models ({len(status['available_models'])}): {status['available_models'][:5]}...")
    assert isinstance(status['available_models'], list), "Available models should be a list"

    # 2. Test candidate data loader
    candidate = tailor_engine.get_candidate_data()
    candidate_name = candidate.get("basics", {}).get("name")
    print(f"[2] Candidate Loaded: {candidate_name}")
    assert candidate_name == "Thomas S. Snyder", f"Expected Thomas S. Snyder, got {candidate_name}"

    # 3. Ensure test job in database
    conn = db.create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, company FROM jobs LIMIT 1")
    job_row = cursor.fetchone()
    
    if not job_row:
        print("[3] Creating test job in database...")
        db.add_job(
            title="Senior QA Automation Lead",
            company="CloudScale AI",
            url="https://example.com/jobs/senior-qa",
            site_source="test_harness",
            score=88,
            missing_skills=["Kubernetes"],
            matched_skills=["Karate Framework", "API Testing", "AWS", "Playwright"]
        )
        cursor.execute("SELECT id, title, company FROM jobs WHERE site_source = 'test_harness' LIMIT 1")
        job_row = cursor.fetchone()

    job_id = job_row[0]
    title = job_row[1]
    company = job_row[2]
    conn.close()

    print(f"[3] Using Job #{job_id}: {title} at {company}")

    # 4. Test tailoring generation
    print("[4] Generating tailored package...")
    res = tailor_engine.tailor_for_job(job_id)
    
    print(f"    Status: {res['status']}")
    print(f"    Output Folder: {res['folder_path']}")
    print(f"    Resume File: {os.path.exists(res['resume_path'])} ({len(res['resume_md'])} chars)")
    print(f"    Cover Letter File: {os.path.exists(res['cover_letter_path'])} ({len(res['cover_letter_md'])} chars)")

    assert os.path.exists(res['resume_path']), "Resume.md must exist"
    assert os.path.exists(res['cover_letter_path']), "Cover_Letter.md must exist"
    assert "Thomas S. Snyder" in res['resume_md'], "Resume must contain candidate name"
    assert company in res['cover_letter_md'], "Cover letter must reference company name"

    # 5. Test existing package retrieval
    existing = tailor_engine.get_existing_tailored_package(job_id)
    print(f"[5] Checking Existing Package: Exists = {existing.get('exists')}")
    assert existing.get("exists") is True, "Existing package should be detected"

    print("\n[SUCCESS] All Tailor Engine tests passed successfully!")

if __name__ == "__main__":
    test_tailor_engine()
