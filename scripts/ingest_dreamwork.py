import argparse
import datetime
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Any, Tuple

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from scripts.database import is_duplicate, add_job
    from scripts.scorer import score_job
    from scripts.profile import get_active_profile, get_profile, validate_config, default_config
except ImportError as err:
    print(f"Error importing TalentScout dependencies: {err}")
    sys.exit(1)

DREAMWORK_API_BASE = "https://api.dreamworkhq.com/listings"
DEFAULT_HEADERS = {
    "User-Agent": "TalentScout/1.0",
    "x-dreamwork-surface": "mcp",
    "Accept": "application/json"
}


def log(msg: str):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")


def job_exists_in_db(url: str, title: Optional[str] = None, company: Optional[str] = None) -> bool:
    """Checks if a job URL or title/company combo is already stored in SQLite."""
    from scripts.database import create_connection
    conn = create_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM jobs WHERE url = ?", (url,))
        if cursor.fetchone():
            return True
        if title and company:
            cursor.execute("SELECT id FROM jobs WHERE title = ? AND company = ?", (title, company))
            if cursor.fetchone():
                return True
        return False
    except Exception:
        return False
    finally:
        conn.close()


def fetch_dreamwork_listings(
    search: str,
    location: Optional[str] = None,
    work_type: Optional[str] = None,
    days_ago: Optional[int] = 14,
    limit: int = 25,
    offset: int = 0
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Queries GET https://api.dreamworkhq.com/listings.
    Returns (listings, total_matching_count).
    """
    params: Dict[str, str] = {
        "search": search.strip(),
        "sort": "newest",
        "limit": str(min(limit, 25)),
        "offset": str(offset)
    }

    if location and location.strip():
        params["location"] = location.strip()

    if work_type and work_type.strip() and work_type.lower() != "any":
        params["workType"] = work_type.strip()

    if days_ago is not None and days_ago > 0:
        params["postedWithin"] = str(days_ago)

    url = f"{DREAMWORK_API_BASE}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=DEFAULT_HEADERS)

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            listings = data.get("listings", [])
            total = data.get("total", len(listings))
            return listings, total
    except urllib.error.HTTPError as e:
        log(f"  [!] Dreamwork API HTTP error ({e.code}): {e.reason}")
        return [], 0
    except Exception as e:
        log(f"  [!] Dreamwork connection error: {e}")
        return [], 0


def fetch_listing_details(listing_id: str) -> Optional[Dict[str, Any]]:
    """
    Queries GET https://api.dreamworkhq.com/listings/{listing_id}
    to retrieve the full description text and metadata.
    """
    url = f"{DREAMWORK_API_BASE}/{listing_id}"
    req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("listing")
    except Exception as e:
        log(f"  [!] Failed to fetch details for listing {listing_id}: {e}")
        return None


def resolve_candidate_profile(
    profile_id: Optional[int] = None,
    skillset_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Dynamically loads the target candidate profile:
    1. If a skillset JSON path is supplied, builds an overlay config on top of default_config().
    2. Else if profile_id is given, loads that profile from the database.
    3. Else defaults to get_active_profile().
    """
    if skillset_path and os.path.exists(skillset_path):
        try:
            with open(skillset_path, "r", encoding="utf-8") as f:
                skillset_data = json.load(f)

            base_cfg = default_config()
            if "name" in skillset_data:
                base_cfg["meta"]["candidate_name"] = skillset_data["name"]
            if "experience_years" in skillset_data:
                base_cfg["meta"]["experience_years"] = skillset_data["experience_years"]
            if "core_skills" in skillset_data:
                base_cfg["scoring"]["core_tech"] = skillset_data["core_skills"]
                base_cfg["search"]["relevant_tech"] = skillset_data["core_skills"]
            if "disqualified_skills" in skillset_data:
                base_cfg["scoring"]["disqualified_skills"] = skillset_data["disqualified_skills"]

            # Location overlay
            loc_data = skillset_data.get("location", {})
            if isinstance(loc_data, dict):
                for k in ["country", "state", "city", "allowed_countries", "target_states", "preferred_cities", "allow_remote"]:
                    if k in loc_data:
                        base_cfg["location"][k] = loc_data[k]
            elif "preferred_locations" in skillset_data:
                base_cfg["location"]["preferred_locations"] = skillset_data["preferred_locations"]

            # Configure title keywords dynamically for custom persona
            core_skills = skillset_data.get("core_skills", [])
            core_lower = {s.lower() for s in core_skills}

            if "title_keywords_positive" in skillset_data:
                base_cfg["search"]["title_keywords_positive"] = skillset_data["title_keywords_positive"]
            elif core_skills:
                # Add non-generic core skills as positive title signals
                base_cfg["search"]["title_keywords_positive"] = [s for s in core_skills if len(s) > 2][:8]

            if "title_keywords_negative" in skillset_data:
                base_cfg["search"]["title_keywords_negative"] = skillset_data["title_keywords_negative"]
            else:
                # Filter out any default negative keywords that conflict with candidate's core skills
                base_cfg["search"]["title_keywords_negative"] = [
                    neg for neg in base_cfg["search"].get("title_keywords_negative", [])
                    if not any(cs in neg.lower() for cs in core_lower)
                ]

            validated = validate_config(base_cfg)
            return {
                "id": 0,
                "name": skillset_data.get("name", "Custom Skillset Profile"),
                "config": validated
            }
        except Exception as e:
            log(f"Warning: Failed to load skillset from {skillset_path}: {e}. Falling back to active profile.")

    if profile_id is not None:
        p = get_profile(profile_id)
        if p:
            return p
        log(f"Warning: Profile ID {profile_id} not found in database. Using active profile.")

    return get_active_profile()


def derive_search_terms(profile: Dict[str, Any], cli_terms: Optional[str] = None) -> List[str]:
    """Extracts or derives search queries based on CLI input, profile config, or core skills."""
    if cli_terms and cli_terms.strip():
        return [t.strip() for t in cli_terms.split(",") if t.strip()]

    cfg = profile.get("config", {})
    terms = cfg.get("search", {}).get("default_terms", [])
    if terms and isinstance(terms, list) and len(terms) > 0:
        return [t for t in terms if t.strip()]

    # Fallback to core tech keywords or candidate target
    core_tech = cfg.get("scoring", {}).get("core_tech", [])
    if core_tech:
        # Take the top 3-4 most prominent core tech items
        return core_tech[:4]

    return ["Software Engineer"]


def update_jobs_to_review_md(new_passed_jobs: List[Dict[str, Any]], new_failed_jobs: List[Dict[str, Any]]) -> None:
    """Appends newly evaluated jobs to jobs_to_review.md adhering to TalentScout table format."""
    md_path = os.path.join(PROJECT_ROOT, "jobs_to_review.md")
    if not os.path.exists(md_path):
        return

    try:
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        split_md = md_content.split("## Disqualified Jobs")
        table_part = split_md[0].rstrip()
        disq_part = split_md[1] if len(split_md) > 1 else ""

        passed_added = 0
        for job in new_passed_jobs:
            url = job["url"]
            # Deduplicate against existing markdown content
            if url in table_part:
                continue

            fr = job.get("filter_results", {})
            score = fr.get("score", 75)
            title = job["title"]
            company = job["company"]
            missing_skills = fr.get("missing_skills", [])
            missing_str = ", ".join(missing_skills[:3]) if missing_skills else "None"

            table_part += f"\n| {score} | {title} | {company} | Dreamwork | {missing_str} | [Apply]({url}) |"
            passed_added += 1

        failed_added = 0
        for job in new_failed_jobs:
            url = job["url"]
            if url in disq_part or url in table_part:
                continue
            fr = job.get("filter_results", {})
            reason = "/".join(fr.get("disqualified_by", ["Unknown"]))
            disq_part += f"\n- {job['title']} ({job['company']}) - **{reason}**"
            failed_added += 1

        if passed_added > 0 or failed_added > 0:
            new_content = table_part + "\n\n## Disqualified Jobs" + disq_part
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            log(f"[*] Appended {passed_added} passed and {failed_added} disqualified entries to jobs_to_review.md")
    except Exception as e:
        log(f"Warning: Failed to update jobs_to_review.md: {e}")


def ingest_dreamwork_jobs(
    terms: Optional[List[str]] = None,
    location: Optional[str] = None,
    work_type: Optional[str] = "remote",
    days_ago: int = 14,
    limit_per_term: int = 25,
    min_score: Optional[int] = None,
    profile_id: Optional[int] = None,
    skillset_path: Optional[str] = None,
    dry_run: bool = False,
    update_md: bool = True
) -> Dict[str, Any]:
    """
    Main ingestion engine:
    1. Loads target candidate profile (QA, Developer, Data, etc.).
    2. Queries Dreamwork API for each search term.
    3. Deduplicates against job_tracker.db.
    4. Fetches full descriptions and scores each role using score_job().
    5. Saves passed roles into database and optionally updates jobs_to_review.md.
    """
    profile = resolve_candidate_profile(profile_id=profile_id, skillset_path=skillset_path)
    cfg = profile.get("config", {})
    profile_name = profile.get("name", "Active Profile")
    p_id = profile.get("id", 1)

    # Derive search terms
    search_terms = terms if (terms and len(terms) > 0) else derive_search_terms(profile)

    # Derive location defaults from profile if not overridden
    loc_cfg = cfg.get("location", {})
    if location is None:
        location = loc_cfg.get("country_name") or loc_cfg.get("country") or "United States"

    # Derive workType defaults from profile
    if work_type is None:
        if loc_cfg.get("allow_remote", True):
            work_type = "remote"
        else:
            work_type = None

    score_threshold = min_score if min_score is not None else cfg.get("scoring", {}).get("min_relevance_score", 40)

    log(f"=== Dreamwork Ingestion Starting ===")
    log(f"Profile: '{profile_name}' (ID: {p_id})")
    log(f"Search Terms: {search_terms}")
    log(f"Location Filter: {location or 'Worldwide'}")
    log(f"Work Type Filter: {work_type or 'Any'}")
    log(f"Min Relevance Score: {score_threshold}")
    log(f"Dry Run: {dry_run}")

    summary = {
        "terms_queried": len(search_terms),
        "total_discovered": 0,
        "duplicates_skipped": 0,
        "evaluated": 0,
        "passed": 0,
        "disqualified": 0,
        "jobs_added": []
    }

    new_passed_jobs = []
    new_failed_jobs = []

    for term in search_terms:
        log(f"\n---> Searching Dreamwork for: '{term}'...")
        offset = 0
        fetched_for_term = 0

        while fetched_for_term < limit_per_term:
            page_limit = min(25, limit_per_term - fetched_for_term)
            listings, total_matching = fetch_dreamwork_listings(
                search=term,
                location=location,
                work_type=work_type,
                days_ago=days_ago,
                limit=page_limit,
                offset=offset
            )

            if not listings:
                if offset == 0:
                    log(f"  [-] No listings found on Dreamwork for '{term}'.")
                break

            summary["total_discovered"] += len(listings)
            log(f"  [*] Retrieved page with {len(listings)} listings (Total available: {total_matching})")

            for item in listings:
                title = item.get("title", "Unknown Title")
                company = item.get("companyName", "Unknown Company")
                # Direct ATS URL (Greenhouse, Lever, Workday, etc.) or Dreamwork fallback link
                job_url = item.get("sourceUrl") or f"https://www.dreamworkhq.com/job/{item.get('id')}"
                listing_id = item.get("id")

                # Step 1: Rapid Duplicate Check against SQLite
                if is_duplicate(job_url, title, company) or job_exists_in_db(job_url, title, company):
                    summary["duplicates_skipped"] += 1
                    continue

                # Step 2: Fetch Full Description
                time.sleep(0.15)  # Friendly pacing
                detail = fetch_listing_details(listing_id)
                jd_text = detail.get("description", "") if detail else ""

                if not jd_text:
                    # Fallback to techStack and title if detail description is unavailable
                    tech_list = item.get("techStack", [])
                    jd_text = f"{title}\n{company}\nTech Stack: {', '.join(tech_list)}"

                # Step 3: Multi-Axis Scoring & Safety Nets
                loc_text = item.get("location") or ""
                country_code = item.get("locationCountryCode") or ""

                score_res = score_job(
                    jd_text,
                    title=title,
                    location=loc_text,
                    country=country_code,
                    company=company,
                    url=job_url,
                    profile_data=profile
                )

                summary["evaluated"] += 1

                job_record = {
                    "title": title,
                    "company": company,
                    "url": job_url,
                    "location": loc_text,
                    "country": country_code or score_res.get("detected_country"),
                    "filter_results": score_res,
                    "salary": item.get("salary")
                }

                if score_res.get("is_disqualified"):
                    summary["disqualified"] += 1
                    reasons = ", ".join(score_res.get("disqualified_by", ["Disqualified"]))
                    log(f"  [-] Disqualified: {title} @ {company} ({reasons})")
                    new_failed_jobs.append(job_record)
                    continue

                score = score_res.get("score", 75)
                if score < score_threshold:
                    summary["disqualified"] += 1
                    log(f"  [-] Below Min Score ({score} < {score_threshold}): {title} @ {company}")
                    score_res["disqualified_by"] = [f"Score below threshold ({score} < {score_threshold})"]
                    new_failed_jobs.append(job_record)
                    continue

                # Step 4: Approved & Passed
                summary["passed"] += 1
                matched = score_res.get("matched_skills", [])
                missing = score_res.get("missing_skills", [])
                salary_str = f" | {item.get('salary')}" if item.get('salary') else ""

                log(f"  [+] MATCH [Score: {score}]: {title} @ {company}{salary_str}")
                log(f"      Direct ATS: {job_url}")
                log(f"      Matched Tech: {', '.join(matched[:5])}")

                new_passed_jobs.append(job_record)
                summary["jobs_added"].append({
                    "title": title,
                    "company": company,
                    "url": job_url,
                    "score": score,
                    "salary": item.get("salary")
                })

                if not dry_run:
                    add_job(
                        title=title,
                        company=company,
                        url=job_url,
                        site_source="Dreamwork",
                        score=score,
                        missing_skills=missing[:3],
                        matched_skills=matched[:5],
                        score_profile_id=p_id,
                        location=loc_text,
                        country=country_code or score_res.get("detected_country")
                    )

            fetched_for_term += len(listings)
            offset += len(listings)

            if len(listings) < page_limit:
                break

    # Step 5: Update Markdown review list if enabled
    if update_md and not dry_run:
        update_jobs_to_review_md(new_passed_jobs, new_failed_jobs)

    log("\n=== Ingestion Summary ===")
    log(f"Total Discovered on Dreamwork: {summary['total_discovered']}")
    log(f"Existing Duplicates Skipped:   {summary['duplicates_skipped']}")
    log(f"New Listings Evaluated:        {summary['evaluated']}")
    log(f"Disqualified / Low Score:      {summary['disqualified']}")
    log(f"Approved & Ingested:           {summary['passed']}")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Ingest job listings from DreamworkHQ into TalentScout without npm/node dependencies."
    )
    parser.add_argument(
        "--terms",
        type=str,
        default=None,
        help="Comma-separated search terms (e.g. 'Software Engineer, Full Stack, React'). Defaults to active profile terms."
    )
    parser.add_argument(
        "--location",
        type=str,
        default=None,
        help="Target location constraint (e.g. 'United States', 'California', or '' for worldwide)."
    )
    parser.add_argument(
        "--work-type",
        type=str,
        default="remote",
        choices=["remote", "hybrid", "onsite", "any"],
        help="Work setting filter (default: remote)."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="Only search postings within the last N days (default: 14)."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="Maximum listings to fetch per term (default: 25)."
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=None,
        help="Override minimum relevance score cutoff (default: from profile)."
    )
    parser.add_argument(
        "--profile-id",
        type=int,
        default=None,
        help="Specific database profile ID to evaluate against."
    )
    parser.add_argument(
        "--skillset",
        type=str,
        default=None,
        help="Path to a custom skillset JSON file (e.g. base_skillset.example.json)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview and score jobs without adding them to SQLite or markdown."
    )
    parser.add_argument(
        "--no-md",
        action="store_true",
        help="Do not update jobs_to_review.md."
    )

    args = parser.parse_args()

    terms_list = [t.strip() for t in args.terms.split(",")] if args.terms else None

    ingest_dreamwork_jobs(
        terms=terms_list,
        location=args.location,
        work_type=args.work_type,
        days_ago=args.days,
        limit_per_term=args.limit,
        min_score=args.min_score,
        profile_id=args.profile_id,
        skillset_path=args.skillset,
        dry_run=args.dry_run,
        update_md=not args.no_md
    )


if __name__ == "__main__":
    main()
