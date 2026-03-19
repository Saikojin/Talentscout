import os
import sys
import json

# Ensure imports work regardless of run location
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.database import add_site, add_search_config, get_all_sites

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    print(f"Warning: {filepath} not found.")
    return {}

def migrate():
    config_file = "site_selectors.json"
    sites_file = "job_search_sites.json"

    configs = load_json(config_file)
    sites_data = load_json(sites_file)

    sites_to_search = sites_data.get("job_search_sites", [])

    print("Migrating site profiles...")
    site_id_map = {}
    for site_name, config in configs.items():
        search_url = config.get("search_url", "")
        job_card_selector = config.get("job_card_selector", "")
        title_selector = config.get("title_selector", "")
        company_selector = config.get("company_selector", "")
        job_url_selector = config.get("job_url_selector", "")

        try:
            site_id = add_site(site_name, search_url, job_card_selector, title_selector, company_selector, job_url_selector)
            if site_id:
                site_id_map[site_name.lower()] = site_id
            else:
                print(f"Failed to add site or already exists: {site_name}")
        except Exception as e:
            print(f"Exception adding site {site_name}: {e}")

    # Fetch all sites in case they were already added
    all_db_sites = get_all_sites()
    for db_site in all_db_sites:
        site_id_map[db_site["name"].lower()] = db_site["id"]

    print("Migrating search configurations...")
    for site in sites_to_search:
        target_name = site["name"]
        
        # Fuzzy match to find the corresponding site_id
        matched_id = None
        for key, site_id in site_id_map.items():
            if key in target_name.lower() or target_name.lower() in key:
                matched_id = site_id
                break
        
        if matched_id:
            search_terms = site.get("search_terms", [])
            locations = site.get("locations", [])
            filters = site.get("filters", {})
            
            c_id = add_search_config(matched_id, search_terms, locations, filters)
            if c_id:
                print(f"Added search config for {target_name}")
            else:
                print(f"Failed to add search config for {target_name}")
        else:
            print(f"Warning: Could not match search config for '{target_name}' to any defined site selector.")

    print("Migration complete!")

if __name__ == "__main__":
    migrate()
