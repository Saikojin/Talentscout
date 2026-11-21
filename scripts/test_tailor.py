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

    # 4. Test tailoring generation (All 7 ATS styles + All 4 Cover Letter audiences + DOCX)
    print("[4] Generating full multi-ATS & multi-tone tailored package...")
    sample_jd = (
        "We are seeking a Staff AI Quality & Automation Architect to build Playwright E2E gates, "
        "MCP agent evaluation harnesses, and scalable API automation across AWS microservices."
    )
    res = tailor_engine.tailor_for_job(job_id, provider="local", cover_letter_tone="jd_informed", job_description=sample_jd)
    
    print(f"    Status: {res['status']}")
    print(f"    Output Folder: {res['folder_path']}")
    print(f"    Files Generated ({len(res['files'])}): {res['files']}")

    assert os.path.exists(res['resume_path']), "Resume.md must exist"
    assert os.path.exists(res['cover_letter_path']), "Cover_Letter.md must exist"
    assert "Thomas S. Snyder" in res['resume_md'], "Resume must contain candidate name"
    assert "SeikoClaw" in res['resume_md'], "Resume must include updated AI/Agentic advancements from resume.json"
    assert company in res['cover_letter_md'], "Cover letter must reference company name"

    # Verify all 7 ATS resume styles (.md + .docx)
    for style in tailor_engine.RESUME_STYLES:
        assert style in res["resumes"], f"Missing resume style: {style}"
        meta = tailor_engine.RESUME_STYLE_META[style]
        md_file = os.path.join(res["folder_path"], meta["filename_md"])
        docx_file = os.path.join(res["folder_path"], meta["filename_docx"])
        assert os.path.exists(md_file), f"Missing {meta['filename_md']}"
        assert os.path.exists(docx_file) and os.path.getsize(docx_file) > 1000, f"Missing or empty {meta['filename_docx']}"

    carl_md = res["resumes"]["CARL"]
    assert "Context:" in carl_md and "Action:" in carl_md and "Result:" in carl_md and "Learning:" in carl_md, "CARL resume must contain Context/Action/Result/Learning"
    assert "Tech Stack & Keywords:" in carl_md, "ATS resumes must include Tech Stack & Keywords line for AI parsers"

    # Verify all 4 Cover Letter audiences (.md + .docx)
    for tone in tailor_engine.COVER_LETTER_TONES:
        assert tone in res["cover_letters"], f"Missing cover letter tone: {tone}"
        t_meta = tailor_engine.COVER_LETTER_TONE_META[tone]
        md_file = os.path.join(res["folder_path"], t_meta["filename_md"])
        docx_file = os.path.join(res["folder_path"], t_meta["filename_docx"])
        assert os.path.exists(md_file), f"Missing {t_meta['filename_md']}"
        assert os.path.exists(docx_file) and os.path.getsize(docx_file) > 1000, f"Missing or empty {t_meta['filename_docx']}"
        assert company in res["cover_letters"][tone], f"{tone} cover letter must mention company"

    # Distinctness check across audiences
    assert res["cover_letters"]["cto"] != res["cover_letters"]["ceo"], "CTO and CEO letters must differ"
    assert res["cover_letters"]["hr"] != res["cover_letters"]["jd_informed"], "HR and JD-Informed letters must differ"

    # 5. Test single-tone cover letter regeneration (CTO) + JD persistence
    print("[5] Testing targeted cover letter regeneration (CTO tone)...")
    regen = tailor_engine.regenerate_cover_letter(job_id, tone="cto", job_description=sample_jd, provider="local")
    assert regen["active_cover_tone"] == "cto"
    assert "CTO" in regen["cover_letters"]["cto"] or "Engineering Leadership" in regen["cover_letters"]["cto"]

    # 6. Test safe file resolution (valid + path traversal blocked)
    valid_path = tailor_engine.get_tailored_file_path(job_id, "Resume_ATS_CARL.docx")
    assert valid_path and os.path.exists(valid_path), "Valid CARL docx path must resolve"
    assert tailor_engine.get_tailored_file_path(job_id, "../job_tracker.db") is None, "Path traversal must be blocked"

    # 7. Test existing package retrieval
    existing = tailor_engine.get_existing_tailored_package(job_id)
    print(f"[7] Checking Existing Package: Exists = {existing.get('exists')}, Styles = {len(existing.get('resumes', {}))}, Tones = {len(existing.get('cover_letters', {}))}")
    assert existing.get("exists") is True, "Existing package should be detected"
    assert len(existing.get("resumes", {})) == 7, "Should load all 7 resume styles"
    assert len(existing.get("cover_letters", {})) == 4, "Should load all 4 cover letter tones"
    assert "Playwright E2E gates" in existing.get("job_description", ""), "Saved JD must persist"

    print("\n[SUCCESS] All Tailor Engine multi-ATS & multi-tone tests passed successfully!")

if __name__ == "__main__":
    test_tailor_engine()
