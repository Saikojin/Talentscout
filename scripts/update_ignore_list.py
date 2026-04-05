import json
import os
import argparse

def update_ignore_skills(results_path, ignore_path):
    """
    Extracts 'missing_skills' from the auto-scour results JSON and adds them
     to the ignore_skills.txt list if they are not already present.
    """
    if not os.path.exists(results_path):
        print(f"Error: {results_path} not found.")
        return

    print(f"Reading results from {results_path}...")
    with open(results_path, 'r', encoding='utf-8') as f:
        try:
            results = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return

    # Extract all missing skills from results
    missing_skills = set()
    for item in results:
        if isinstance(item, dict) and 'filter_results' in item:
            filter_results = item['filter_results']
            if 'missing_skills' in filter_results and isinstance(filter_results['missing_skills'], list):
                for skill in filter_results['missing_skills']:
                    if skill and isinstance(skill, str):
                        missing_skills.add(skill.strip())

    # Read existing ignore list
    existing_ignore = set()
    if os.path.exists(ignore_path):
        with open(ignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                skill = line.strip()
                if skill:
                    existing_ignore.add(skill)

    # Find only new skills
    new_skills = missing_skills - existing_ignore
    
    if not new_skills:
        print("No new skills to add.")
        return

    # Merge and sort
    all_skills = sorted(list(existing_ignore | new_skills), key=str.lower)

    print(f"Found {len(new_skills)} new skills to add.")
    
    # Backup existing file before overwrite (optional but safer)
    # with open(ignore_path + '.bak', 'w', encoding='utf-8') as f:
    #     for skill in sorted(list(existing_ignore), key=str.lower):
    #         f.write(skill + '\n')

    with open(ignore_path, 'w', encoding='utf-8') as f:
        for skill in all_skills:
            f.write(skill + '\n')

    print(f"Successfully updated {ignore_path}.")
    print(f"Added: {', '.join(sorted(list(new_skills))[:10])}{'...' if len(new_skills) > 10 else ''}")

if __name__ == "__main__":
    # Get the project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    # Default paths
    default_results = os.path.join(project_root, 'logs', 'auto_scour_results.json')
    default_ignore = os.path.join(project_root, 'ignore_skills.txt')

    parser = argparse.ArgumentParser(description="Update ignore_skills.txt with new missing skills from scour results.")
    parser.add_argument("--results", default=default_results, help="Path to the auto_scour_results.json file")
    parser.add_argument("--ignore", default=default_ignore, help="Path to the ignore_skills.txt file")
    
    args = parser.parse_args()

    update_ignore_skills(args.results, args.ignore)
