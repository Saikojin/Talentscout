import argparse
import json
import os
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from scripts.scorer import score_job
from scripts.profile import get_active_profile
from scripts.location_utils import evaluate_job_location
from scripts.auto_scour import is_non_job_url

SCOUR_RESULTS_FILE = os.path.join(BASE_DIR, "logs", "auto_scour_results.json")
DB_PATH = os.path.join(BASE_DIR, "job_tracker.db")

def prune_scour_json(apply_changes: bool = False, json_path: str = SCOUR_RESULTS_FILE):
    """
    Check or prune existing auto_scour_results.json using updated scorer,
    location, empty-JD, and URL rules.
    """
    if not os.path.exists(json_path):
        print(f"[!] Scour results file not found at: {json_path}")
        return

    print("=" * 60)
    print(f"[*] Analyzing Scour Results: {json_path}")
    print("=" * 60)

    with open(json_path, "r", encoding="utf-8") as f:
        try:
            scour_data = json.load(f)
        except Exception as e:
            print(f"[!] Error parsing JSON: {e}")
            return

    if not isinstance(scour_data, list):
        print("[!] Invalid JSON structure (expected a list of jobs).")
        return

    active_profile = get_active_profile()
    profile_name = active_profile.get("name", "Active Profile")
    print(f"[*] Active Profile: {profile_name}")
    print(f"[*] Total Harvested Entries: {len(scour_data)}")

    old_passed_count = 0
    new_passed_count = 0
    pruned_count = 0
    disqualification_breakdown = {}
    pruned_sample = []

    for job in scour_data:
        was_passed = not job.get("filter_results", {}).get("is_disqualified", True)
        if was_passed:
            old_passed_count += 1

        url = job.get("url", "")
        if is_non_job_url(url):
            filter_res = {
                "is_disqualified": True,
                "disqualified_by": ["Non-Job Landing / Category URL"],
                "matched_skills": [],
                "missing_skills": [],
                "score": 0,
                "score_breakdown": {"title": 0, "tech": 0, "experience": 0, "signal": 0},
                "experience_level": "unknown",
                "detected_country": None,
                "score_profile_id": active_profile.get("id", 1)
            }
        else:
            filter_res = score_job(
                job.get("description", ""),
                title=job.get("title", ""),
                location=job.get("location", ""),
                country=job.get("country", ""),
                company=job.get("company", ""),
                url=url,
                profile_data=active_profile
            )

        job["filter_results"] = filter_res

        if not filter_res.get("is_disqualified"):
            new_passed_count += 1
        else:
            if was_passed:
                pruned_count += 1
                for reason in filter_res.get("disqualified_by", []):
                    disqualification_breakdown[reason] = disqualification_breakdown.get(reason, 0) + 1
                if len(pruned_sample) < 10:
                    pruned_sample.append({
                        "title": job.get("title"),
                        "company": job.get("company"),
                        "url": job.get("url"),
                        "score": filter_res.get("score"),
                        "reasons": filter_res.get("disqualified_by")
                    })

    print(f"\n[+] Previously Passing Jobs: {old_passed_count}")
    print(f"[+] Newly Passing Jobs:      {new_passed_count}")
    print(f"[-] Total Jobs Pruned:       {pruned_count}")

    if disqualification_breakdown:
        print("\n--- Pruning Reasons Breakdown ---")
        for reason, count in sorted(disqualification_breakdown.items(), key=lambda x: x[1], reverse=True):
            print(f"  * {reason}: {count}")

    if pruned_sample:
        print("\n--- Sample of Pruned Roles ---")
        for idx, sample in enumerate(pruned_sample, 1):
            print(f"  {idx}. {sample['title']} at {sample['company']}")
            print(f"     URL: {sample['url']}")
            print(f"     New Score: {sample['score']} | Reasons: {', '.join(sample['reasons'])}")

    if apply_changes:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(scour_data, f, indent=2)
        print(f"\n[SUCCESS] Updated {json_path} with new filter evaluations.")
    else:
        print(f"\n[INFO] Dry-run complete. Run with --apply to overwrite {json_path}.")


def prune_database(apply_changes: bool = False, db_path: str = DB_PATH):
    """
    Check or prune jobs in job_tracker.db that violate location, URL, or empty-JD rules.
    """
    if not os.path.exists(db_path):
        print(f"[!] Database not found at: {db_path}")
        return

    print("\n" + "=" * 60)
    print(f"[*] Analyzing Database Jobs: {db_path}")
    print("=" * 60)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, company, url, location, country, score, status FROM jobs")
    rows = cursor.fetchall()
    total_db_jobs = len(rows)
    print(f"[*] Total Jobs in DB: {total_db_jobs}")

    active_profile = get_active_profile()
    loc_cfg = active_profile.get("config", {}).get("location", {})

    invalid_ids = []
    reasons_count = {}
    sample_pruned = []

    for r in rows:
        jid, title, company, url, location, country, score, status = r

        # 1. Non-job URL check
        if is_non_job_url(url):
            invalid_ids.append(jid)
            reasons_count["Non-Job Landing URL"] = reasons_count.get("Non-Job Landing URL", 0) + 1
            if len(sample_pruned) < 10:
                sample_pruned.append((jid, title, company, "Non-Job Landing URL"))
            continue

        # 2. Location & Country validation
        loc_eval = evaluate_job_location(
            location=location or "",
            country=country or "",
            title=title or "",
            jd_text="",
            company=company or "",
            url=url or "",
            profile_location=loc_cfg
        )

        if loc_eval.get("is_disqualified"):
            invalid_ids.append(jid)
            reason = loc_eval.get("reason", "Location Disqualified")
            reasons_count[reason] = reasons_count.get(reason, 0) + 1
            if len(sample_pruned) < 10:
                sample_pruned.append((jid, title, company, reason))

    print(f"[-] Total DB Jobs Flagged for Pruning: {len(invalid_ids)} / {total_db_jobs}")

    if reasons_count:
        print("\n--- DB Pruning Reasons Breakdown ---")
        for reason, count in sorted(reasons_count.items(), key=lambda x: x[1], reverse=True)[:15]:
            print(f"  * {reason}: {count}")

    if sample_pruned:
        print("\n--- Sample of Flagged DB Roles ---")
        for jid, title, company, reason in sample_pruned:
            print(f"  [ID #{jid}] {title} at {company} -> {reason}")

    if apply_changes and invalid_ids:
        # Delete invalid 'new' jobs from database
        cursor.execute(f"DELETE FROM jobs WHERE id IN ({','.join(['?']*len(invalid_ids))})", invalid_ids)
        conn.commit()
        print(f"\n[SUCCESS] Deleted {len(invalid_ids)} disqualified jobs from {db_path}.")
    elif not apply_changes:
        print(f"\n[INFO] Dry-run complete. Run with --apply to remove disqualified jobs from DB.")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Prune bad or out-of-country entries from scour results and database.")
    parser.add_argument("--apply", action="store_true", help="Apply pruning changes directly to file/database")
    parser.add_argument("--target", choices=["all", "json", "db"], default="all", help="Target to prune (all, json, or db)")
    args = parser.parse_args()

    if args.target in ("all", "json"):
        prune_scour_json(apply_changes=args.apply)

    if args.target in ("all", "db"):
        prune_database(apply_changes=args.apply)

if __name__ == "__main__":
    main()
