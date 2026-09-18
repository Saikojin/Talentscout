import re
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from scripts.profile import get_active_profile
from scripts.filter_skills import filter_job as fallback_filter_skills
from scripts.location_utils import evaluate_job_location, normalize_country

def estimate_experience_level(text: str) -> str:
    """Guess experience level from job description text."""
    text_lower = text.lower()
    if any(w in text_lower for w in [
        "intern", "internship", "trainee", "entry level", "entry-level",
        "0-1 year", "0-2 years", "fresher", "new grad", "graduate",
        "campus", "freshers", "b.tech", "b.e.", "mca"
    ]):
        return "fresher"
    if any(w in text_lower for w in [
        "senior", "sr.", "lead", "principal", "staff", "architect",
        "8+ years", "10+ years", "15+ years", "20+ years"
    ]):
        return "senior"
    if any(w in text_lower for w in [
        "junior", "jr.", "1+ year", "1-2 years"
    ]):
        return "junior"
    if any(w in text_lower for w in [
        "mid", "middle", "3+ years", "2+ years", "4+ years", "5+ years",
        "3-5 years", "2-4 years", "4-6 years"
    ]):
        return "mid"
    return "mid"

def score_job(
    jd_text: str,
    title: str = "",
    location: str = "",
    country: str = "",
    company: str = "",
    url: str = "",
    profile_data: dict = None
) -> dict:
    """
    Score a job using multi-axis weighted scoring based on the active profile.
    Enforces country allowances (US-only default), location constraints,
    empty JD safety net, and skill matching.
    """
    if profile_data is None:
        profile_obj = get_active_profile()
        profile_id = profile_obj.get("id")
        cfg = profile_obj.get("config", {})
    else:
        profile_id = profile_data.get("id", 0)
        cfg = profile_data.get("config", profile_data)

    search_cfg = cfg.get("search", {})
    scoring_cfg = cfg.get("scoring", {})
    loc_cfg = cfg.get("location", {})
    meta_cfg = cfg.get("meta", {})

    disqualified_by = []
    matched_skills = []
    missing_skills = []

    jd_clean = (jd_text or "").strip()
    jd_lower = jd_clean.lower()
    title_lower = (title or "").lower()
    is_empty_jd = len(jd_clean) < 50

    # 0. Empty / Invalid Job Description Safety Net Guard
    if is_empty_jd:
        disqualified_by.append("SafetyNet: Empty or invalid job description")

    # 0b. Evaluate Location & Country Restrictions (Strict Country & Safety Net)
    loc_eval = evaluate_job_location(
        location=location,
        country=country,
        title=title,
        jd_text=jd_text,
        company=company,
        url=url,
        profile_location=loc_cfg
    )
    if loc_eval.get("is_disqualified") and loc_eval.get("reason"):
        disqualified_by.append(loc_eval["reason"])

    # 1. Disqualified Skills check
    disqualified_skills = scoring_cfg.get("disqualified_skills", [])
    for skill in disqualified_skills:
        if re.search(rf'\b{re.escape(skill.lower())}\b', jd_lower):
            disqualified_by.append(f"Disqualified Skill: {skill}")

    # 2. Negative Title Keywords check
    title_negatives = search_cfg.get("title_keywords_negative", [])
    for neg_title in title_negatives:
        if neg_title.lower() in title_lower:
            disqualified_by.append(f"Negative Title Keyword: {neg_title}")

    # 3. Location negative check
    loc_negatives = loc_cfg.get("location_negative", [])
    for loc_neg in loc_negatives:
        if loc_neg.lower() in jd_lower:
            disqualified_by.append(f"Location Restricted: {loc_neg}")

    # Axis 1: Title Score (Weight default 30)
    title_score = 0 # Baseline 0 if no positive title keywords match
    title_positives = search_cfg.get("title_keywords_positive", [])
    title_matches = [p for p in title_positives if p.lower() in title_lower]
    if title_matches:
        title_score = min(100, 70 + (len(title_matches) * 15))

    # Axis 2: Tech Score (Weight default 35)
    core_tech = scoring_cfg.get("core_tech", [])
    relevant_tech = search_cfg.get("relevant_tech", [])
    all_tech = list(dict.fromkeys(core_tech + relevant_tech))

    for tech in all_tech:
        if re.search(rf'\b{re.escape(tech.lower())}\b', jd_lower):
            matched_skills.append(tech)
        else:
            if tech in core_tech:
                missing_skills.append(tech)

    tech_score = 0
    if core_tech:
        matched_core = [t for t in core_tech if t in matched_skills]
        tech_score = int((len(matched_core) / len(core_tech)) * 100)
    elif matched_skills:
        tech_score = min(100, len(matched_skills) * 15)

    # Axis 3: Experience Score (Weight default 20)
    if is_empty_jd:
        detected_exp = "unknown"
        exp_score = 0
    else:
        detected_exp = estimate_experience_level(jd_text)
        target_exp = meta_cfg.get("experience_target", "senior")
        exp_bonuses = scoring_cfg.get("experience_bonuses", {})
        exp_bonus_val = exp_bonuses.get(target_exp, {}).get(detected_exp, 5) if isinstance(exp_bonuses.get(target_exp), dict) else exp_bonuses.get(detected_exp, 5)
        exp_score = min(100, max(0, 70 + exp_bonus_val * 2))

    # Axis 4: Signal / Location Score (Weight default 15)
    if is_empty_jd:
        signal_score = 0
    elif loc_eval.get("is_target") or loc_eval.get("is_wa"):
        signal_score = 100
    elif loc_eval.get("is_remote"):
        signal_score = 85
    else:
        loc_positives = loc_cfg.get("location_positive", [])
        loc_matches = [loc for loc in loc_positives if loc.lower() in jd_lower]
        signal_score = min(100, 50 + (len(loc_matches) * 15)) if loc_matches else 50

    # Calculate Weighted Final Score
    weights = scoring_cfg.get("weights", {"title": 30, "tech": 35, "experience": 20, "signal": 15})
    w_title = weights.get("title", 30)
    w_tech = weights.get("tech", 35)
    w_exp = weights.get("experience", 20)
    w_sig = weights.get("signal", 15)
    total_w = max(1, w_title + w_tech + w_exp + w_sig)

    final_score = int((
        (title_score * w_title) +
        (tech_score * w_tech) +
        (exp_score * w_exp) +
        (signal_score * w_sig)
    ) / total_w)

    min_score = scoring_cfg.get("min_relevance_score", 40)
    if final_score < min_score:
        disqualified_by.append(f"Score below threshold ({final_score} < {min_score})")

    is_disqualified = len(disqualified_by) > 0

    return {
        "is_disqualified": is_disqualified,
        "disqualified_by": disqualified_by,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills[:5],
        "score": final_score,
        "score_breakdown": {
            "title": title_score,
            "tech": tech_score,
            "experience": exp_score,
            "signal": signal_score
        },
        "experience_level": detected_exp,
        "detected_country": loc_eval.get("detected_country"),
        "score_profile_id": profile_id
    }


if __name__ == "__main__":
    sample_jd = "Looking for a Senior QA Engineer with Karate Framework, API Testing, Docker and AWS experience in Seattle, WA."
    res = score_job(sample_jd, title="Senior QA Engineer")
    print(json.dumps(res, indent=2))
