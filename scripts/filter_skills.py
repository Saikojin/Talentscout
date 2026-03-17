import json
import re
import sys

IGNORE_LIST = {
    "the", "and", "for", "with", "this", "that", "from", "into", "your", "will",
    "have", "work", "team", "each", "both", "such", "than", "been", "where",
    "these", "those", "when", "while", "what", "which", "who", "whom", "whose",
    "must", "haves", "nices", "offer", "plus", "days", "years", "each", "long",
    "term", "good", "fast", "some", "past", "help", "role", "grow", "make",
    "feel", "most", "also", "take", "give", "stay", "back", "next", "over",
    "full", "time", "high"
}

def filter_job(job_description, base_skillset_path):
    with open(base_skillset_path, 'r') as f:
        skillset = json.load(f)
    
    core_skills = skillset.get('core_skills', [])
    disqualified_skills = skillset.get('disqualified_skills', [])
    
    findings = {
        "is_disqualified": False,
        "disqualified_by": [],
        "missing_skills": [],
        "matched_skills": []
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
    potential_tech_terms = set(re.findall(r'\b[A-Z]{2,}\b|\b[A-Z][a-z]+[A-Z][a-z]+\b|\b[A-Z][a-z]+\d+\b', job_description))
    
    # Filter out common English words and already matched skills
    for term in potential_tech_terms:
        term_lower = term.lower()
        if term_lower not in [s.lower() for s in core_skills] and term_lower not in IGNORE_LIST:
             if term not in findings["matched_skills"]:
                findings["missing_skills"].append(term)
    
    # Deduplicate and sort
    findings["missing_skills"] = sorted(list(set(findings["missing_skills"])))
    
    return findings

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python filter_skills.py <job_description_file> <base_skillset_json>")
        sys.exit(1)
        
    with open(sys.argv[1], 'r', encoding='utf-8') as f:
        jd = f.read()
        
    results = filter_job(jd, sys.argv[2])
    print(json.dumps(results, indent=2))
