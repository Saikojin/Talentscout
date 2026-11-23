"""
Idempotent bootstrap for scheduled/CI TalentScout runs (GitHub Actions, GitLab CI, cron, etc.).

Responsibilities:
  1. Ensure SQLite schema is initialized (`job_tracker.db`).
  2. Seed sites/search_configs and companies from tracked JSON fixtures if empty.
  3. Sync private profiles & email delivery targets from environment secrets without
     ever logging unmasked email addresses or credentials to public CI logs.
  4. Optionally print delivery-enabled profile IDs (JSON) for multi-profile orchestration.
"""
import argparse
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from scripts.database import create_connection, init_db
from scripts.profile import (
    get_delivery_enabled_profiles,
    list_profiles,
    seed_default_profile,
    sync_profiles_from_env,
)


def mask_email(addr: str) -> str:
    """Mask an email address so public CI logs never expose PII."""
    addr = (addr or "").strip()
    if "@" not in addr:
        return "***" if addr else "(none)"
    local, domain = addr.split("@", 1)
    prefix = local[0] if local else "*"
    return f"{prefix}***@{domain}"


def _table_count(table_name: str) -> int:
    conn = create_connection()
    if not conn:
        return 0
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        row = cur.fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


def bootstrap_ci_database(seed_companies: bool = True) -> dict:
    """Initialize DB, seed static config tables if empty, and sync profiles from env secrets."""
    init_db()
    seed_default_profile()

    summary = {
        "sites_before": _table_count("sites"),
        "companies_before": _table_count("companies"),
        "jobs_before": _table_count("jobs"),
        "seeded_sites": False,
        "seeded_companies": False,
    }

    if summary["sites_before"] == 0:
        from scripts.migrate_jsons_to_db import migrate
        migrate()
        summary["seeded_sites"] = True

    if seed_companies and summary["companies_before"] == 0 and os.path.exists(os.path.join(BASE_DIR, "base_companies.json")):
        from scripts.ingest_companies import ingest_companies
        ingest_companies()
        summary["seeded_companies"] = True

    synced = sync_profiles_from_env()
    delivery_profiles = get_delivery_enabled_profiles()

    summary["sites_after"] = _table_count("sites")
    summary["companies_after"] = _table_count("companies")
    summary["jobs_after"] = _table_count("jobs")
    summary["total_profiles"] = len(list_profiles())
    summary["synced_from_env"] = len(synced)
    summary["delivery_profiles"] = [
        {
            "id": p["id"],
            "name": p["name"],
            "recipient_masked": mask_email(p["config"]["delivery"]["recipient_email"]),
            "min_score": p["config"]["delivery"]["min_score"],
            "max_jobs": p["config"]["delivery"]["max_jobs"],
        }
        for p in delivery_profiles
    ]
    return summary


def main(args=None):
    parser = argparse.ArgumentParser(description="Bootstrap TalentScout DB and secret profiles for scheduled CI runs.")
    parser.add_argument("--skip-companies", action="store_true", help="Skip seeding base_companies.json when companies table is empty.")
    parser.add_argument("--list-profile-ids", action="store_true", help="Print space-separated profile IDs to crawl (delivery-enabled, or default profile if none).")
    cli_args = parser.parse_args(args)

    summary = bootstrap_ci_database(seed_companies=not cli_args.skip_companies)

    if cli_args.list_profile_ids:
        ids = [str(p["id"]) for p in summary["delivery_profiles"]]
        if not ids:
            profiles = list_profiles()
            if profiles:
                ids = [str(profiles[0]["id"])]
        print(" ".join(ids))
        return

    print("[*] TalentScout CI Bootstrap Complete:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
