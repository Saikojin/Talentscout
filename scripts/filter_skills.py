import os
import json
import re


def load_ignore_list():
    # Look for ignore_skills.txt in the project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    ignore_path = os.path.join(root_dir, "ignore_skills.txt")
    
    if os.path.exists(ignore_path):
        with open(ignore_path, 'r', encoding='utf-8') as f:
            return {line.strip().lower() for line in f if line.strip()}
    return set()

IGNORE_LIST = load_ignore_list()



def filter_job(job_description, base_skillset_path):
    with open(base_skillset_path, 'r') as f:
        skillset = json.load(f)
    
    core_skills = skillset.get('core_skills', [])
    disqualified_skills = skillset.get('disqualified_skills', [])
    
    findings = {
        "is_disqualified": False,
        "disqualified_by": [],
        "missing_skills": [],
        "matched_skills": [],
        "score": 0
    }
    
    # Check for disqualified skills
    for skill in disqualified_skills:
        if re.search(rf'\b{re.escape(skill)}\b', job_description, re.IGNORECASE):
            findings["is_disqualified"] = True
            findings["disqualified_by"].append(skill)
            
    # Simple keyword matching for core skills
    for skill in core_skills:
        if re.search(rf'\b{re.escape(skill)}\b', job_description, re.IGNORECASE):
            findings["matched_skills"].append(skill)
            
    # Look for common technical patterns (uppercase acronyms, CamelCase, tool names)
    # that are NOT in our core_skills or matched_skills.
    # Refined: Only 2-5 chars for acronyms to avoid common long capitalized words, 
    # or CamelCase, or names with numbers.
    potential_tech_terms = set(re.findall(r'\b[A-Z]{2,6}\b|\b[A-Z][a-z]+[A-Z][a-z]+\b|\b[A-Z][a-z]+\d+\b', job_description))

    
    # Filter out common English words and already matched skills
    for term in potential_tech_terms:
        term_lower = term.lower()
        if term_lower not in [s.lower() for s in core_skills] and term_lower not in IGNORE_LIST:
             if term not in findings["matched_skills"]:
                findings["missing_skills"].append(term)
    
    # Deduplicate and sort
    findings["missing_skills"] = sorted(list(set(findings["missing_skills"])))
    
    # Calculate score based on matched core skills
    if core_skills:
        findings["score"] = int((len(findings["matched_skills"]) / len(core_skills)) * 100)
    else:
        findings["score"] = 75
        
    # -- Location Filtering Heuristics --
    loc_cfg = skillset.get('location', {})
    try:
        from scripts.location_utils import evaluate_job_location
        loc_eval = evaluate_job_location(
            location="",
            country="",
            title="",
            jd_text=job_description,
            profile_location=loc_cfg
        )
        if loc_eval.get("is_disqualified") and loc_eval.get("reason"):
            findings["is_disqualified"] = True
            findings["disqualified_by"].append(loc_eval["reason"])
    except ImportError:
        pass
    
    # 0. Score is 0 (No Matching Skills)
    if findings["score"] == 0:
        findings["is_disqualified"] = True
        findings["disqualified_by"].append("No matching core skills")
    
    return findings


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python filter_skills.py <job_description_file> <base_skillset_json>")
        sys.exit(1)
        
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        jd = f.read()
        
    results = filter_job(jd, sys.argv[2])
    print(json.dumps(results, indent=2))
