"""
Import a TalentScout email digest package (.zip or jobs_delta.json) into the local
SQLite database (`job_tracker.db`) idempotently.

Usage:
    python scripts/import_package.py path/to/talentscout_default-profile_20261122.zip
    python scripts/import_package.py path/to/jobs_delta.json --dry-run
"""
import argparse
import json
import os
import sys
import zipfile
from typing import List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from scripts.database import add_job, canonicalize_job_url, init_db, job_exists
from scripts.profile import get_active_profile, get_profile, get_profile_by_name


def load_package_payload(package_path: str) -> Tuple[dict, List[dict]]:
    """Read manifest/metadata and job list from either a .zip package or a jobs_delta.json file."""
    if not os.path.exists(package_path):
        raise FileNotFoundError(f"Package not found: {package_path}")

    if zipfile.is_zipfile(package_path):
        with zipfile.ZipFile(package_path, "r") as zf:
            names = set(zf.namelist())
            if "jobs_delta.json" not in names:
                raise ValueError(f"Archive '{package_path}' does not contain jobs_delta.json.")
            payload = json.loads(zf.read("jobs_delta.json").decode("utf-8"))
            manifest = json.loads(zf.read("manifest.json").decode("utf-8")) if "manifest.json" in names else {}
            return manifest, payload.get("jobs", [])

    with open(package_path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if isinstance(payload, list):
        return {}, payload
    return payload, payload.get("jobs", [])


def import_package(
    package_path: str,
    profile_arg: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """Import jobs from a TalentScout package into SQLite. Idempotent via URL uniqueness."""
    init_db()
    manifest, jobs = load_package_payload(package_path)

    target_profile_id = None
    if profile_arg:
        prof = get_profile(int(profile_arg)) if profile_arg.isdigit() else get_profile_by_name(profile_arg)
        if not prof:
            raise ValueError(f"Profile '{profile_arg}' not found.")
        target_profile_id = prof["id"]
    else:
        active = get_active_profile()
        target_profile_id = active.get("id")

    imported = 0
    skipped_duplicate = 0
    skipped_invalid = 0
    seen_in_batch = set()

    for job in jobs:
        url = (job.get("url") or "").strip()
        title = (job.get("title") or "").strip()
        company = (job.get("company") or "").strip()
        if not url or not title:
            skipped_invalid += 1
            continue

        clean_url = canonicalize_job_url(url) or url
        batch_key = (clean_url, title.lower(), company.lower())
        if clean_url in seen_in_batch or batch_key in seen_in_batch or job_exists(clean_url, title=title, company=company):
            skipped_duplicate += 1
            continue

        seen_in_batch.add(clean_url)
        seen_in_batch.add(batch_key)

        if dry_run:
            imported += 1
            continue

        inserted_id = add_job(
            title=title,
            company=company or "Unknown",
            url=clean_url,
            site_source=job.get("site_source") or "EmailPackage",
            score=job.get("score"),
            missing_skills=job.get("missing_skills"),
            matched_skills=job.get("matched_skills"),
            score_profile_id=target_profile_id,
            location=job.get("location"),
            country=job.get("country"),
            description=job.get("description") or None,
        )
        if inserted_id is not None:
            imported += 1
        else:
            skipped_duplicate += 1

    return {
        "package": os.path.basename(package_path),
        "run_id": manifest.get("run_id"),
        "profile_id": target_profile_id,
        "total_in_package": len(jobs),
        "imported": imported,
        "skipped_duplicate": skipped_duplicate,
        "skipped_invalid": skipped_invalid,
        "skipped_existing_or_invalid": skipped_duplicate + skipped_invalid,
        "dry_run": dry_run,
    }


def main(args=None):
    parser = argparse.ArgumentParser(description="Import a TalentScout email package (.zip or .json) into local SQLite.")
    parser.add_argument("package", help="Path to talentscout_*.zip or jobs_delta.json")
    parser.add_argument("--profile", type=str, default=None, help="Target local profile ID or name (defaults to active profile).")
    parser.add_argument("--dry-run", action="store_true", help="Inspect package without modifying job_tracker.db.")
    cli_args = parser.parse_args(args)

    summary = import_package(cli_args.package, profile_arg=cli_args.profile, dry_run=cli_args.dry_run)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
