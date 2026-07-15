#!/usr/bin/env python3
import json
import os

RESUME_PATH = os.path.join(os.path.dirname(__file__), "..", "resume", "data", "resume.json")

def load_resume():
    if not os.path.exists(RESUME_PATH):
        print(f"Error: resume.json not found at {RESUME_PATH}")
        return None
    try:
        with open(RESUME_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading resume: {e}")
        return None

def save_resume(data):
    try:
        with open(RESUME_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Successfully updated and saved resume to {RESUME_PATH}!")
    except Exception as e:
        print(f"Error saving resume: {e}")

def get_input(prompt, current_val=None):
    if current_val:
        display = f"{prompt} [{current_val}]: "
    else:
        display = f"{prompt}: "
    val = input(display).strip()
    return val if val else current_val

def get_list_input(prompt, current_list=None):
    print(f"\n--- {prompt} ---")
    if current_list:
        print("Current items:")
        for idx, item in enumerate(current_list, 1):
            print(f"  {idx}. {item}")
        print("Entering new items will REPLACE the existing list. Leave first line empty to keep current items.")
    
    new_list = []
    first = True
    while True:
        item = input(f"Add item (or press Enter to finish): ").strip()
        if not item:
            if first and current_list:
                return current_list
            break
        new_list.append(item)
        first = False
    return new_list

def main():
    print("====================================================")
    print("    TalentScout Detailed Work History Interviewer   ")
    print("====================================================")
    
    resume = load_resume()
    if not resume:
        return

    work_list = resume.get("work", [])
    if not work_list:
        print("No work history found. Let's add a new work history item.")
        resume["work"] = []
        work_list = resume["work"]
    
    print("\nSelect an entry to edit, or add a new one:")
    for idx, job in enumerate(work_list, 1):
        print(f"  {idx}. {job.get('name', 'Unknown Company')} — {job.get('position', 'Unknown Position')}")
    print(f"  {len(work_list) + 1}. Add new work history item")
    
    choice = input(f"Enter choice (1-{len(work_list) + 1}): ").strip()
    
    try:
        choice_idx = int(choice)
    except ValueError:
        print("Invalid input. Exiting.")
        return
        
    if choice_idx == len(work_list) + 1:
        job = {
            "name": "",
            "position": "",
            "startDate": "",
            "endDate": "",
            "summary": "",
            "highlights": []
        }
        is_new = True
    elif 1 <= choice_idx <= len(work_list):
        job = work_list[choice_idx - 1]
        is_new = False
    else:
        print("Out of range choice. Exiting.")
        return

    print("\nLet's fill out the details. Press Enter to keep current values.")
    
    job["name"] = get_input("Company/Organization Name", job.get("name"))
    job["position"] = get_input("Role / Job Title", job.get("position"))
    job["startDate"] = get_input("Start Date (e.g. YYYY-MM-DD, YYYY-MM, or Year)", job.get("startDate"))
    job["endDate"] = get_input("End Date (or empty for Present)", job.get("endDate", ""))
    job["location"] = get_input("Location (e.g. City, State / Remote)", job.get("location"))
    job["summary"] = get_input("General Description / Summary", job.get("summary"))
    
    job["highlights"] = get_list_input("Highlights", job.get("highlights", []))
    job["keyResponsibilities"] = get_list_input("Key Responsibilities", job.get("keyResponsibilities", []))
    job["skillsUsed"] = get_list_input("Skills Used", job.get("skillsUsed", []))
    job["toolsUsed"] = get_list_input("Tools Used", job.get("toolsUsed", []))
    job["challenges"] = get_list_input("Challenges Faced", job.get("challenges", []))
    job["wins"] = get_list_input("Wins / Accomplishments", job.get("wins", []))
    job["lessonsLearned"] = get_list_input("Lessons Learned", job.get("lessonsLearned", []))

    if is_new:
        work_list.append(job)
        
    save_resume(resume)

if __name__ == "__main__":
    main()
