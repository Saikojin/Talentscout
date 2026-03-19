import sqlite3
import os
import sys

# Ensure imports work regardless of run location
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.database import (
    add_site, get_all_sites, update_site, delete_site,
    add_search_config, get_all_search_configs, update_search_config, delete_search_config
)

def test_crud():
    print("Testing Site CRUD...")
    # Add a site
    site_id = add_site("TestSite", "http://test.com/search?q={search_term}", ".card", "h1", ".comp", "a")
    if site_id:
        print(f"Passed: Added site with ID {site_id}")
    else:
        print("Failed: Could not add site")

    # Get sites
    sites = get_all_sites()
    if any(s['name'] == "TestSite" for s in sites):
        print("Passed: Found 'TestSite' in DB")
    else:
        print("Failed: 'TestSite' not found")

    # Update site
    update_site(site_id, "TestSite Updated", "http://test.com/search", ".card2", "h2", ".comp2", "a2")
    sites = get_all_sites()
    if any(s['name'] == "TestSite Updated" for s in sites):
        print("Passed: Updated 'TestSite'")
    else:
        print("Failed: Did not update 'TestSite'")

    # Testing Config CRUD
    print("\nTesting Search Config CRUD...")
    config_id = add_search_config(site_id, ["Test QA"], ["Seattle"], {"type": "full"})
    if config_id:
        print(f"Passed: Added config with ID {config_id}")
    else:
        print("Failed: Could not add search config")

    # Get configs
    configs = get_all_search_configs()
    found_config = next((c for c in configs if c['site_name'] == "TestSite Updated"), None)
    if found_config and "Test QA" in found_config['search_terms']:
        print("Passed: Found correctly joined configs")
    else:
        print("Failed: Could not find joined configs correctly")

    # Delete config
    delete_search_config(config_id)
    configs = get_all_search_configs()
    if not any(c['id'] == config_id for c in configs):
        print("Passed: Deleted search config")
    else:
        print("Failed: Config still exists")

    # Delete site
    delete_site(site_id)
    sites = get_all_sites()
    if not any(s['id'] == site_id for s in sites):
        print("Passed: Deleted site")
    else:
        print("Failed: Site still exists after delete")

if __name__ == "__main__":
    test_crud()
