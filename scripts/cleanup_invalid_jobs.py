import asyncio
import aiohttp
import sqlite3
import os
import sys
from bs4 import BeautifulSoup

# Ensure imports work regardless of execution location
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.profile import get_active_profile
from scripts.scorer import score_job
from scripts.database import DB_PATH

async def fetch_jd_text(session, url):
    if not url or not url.startswith("http"):
        return ""
    try:
        async with session.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"}) as resp:
            if resp.status != 200:
                return ""
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            # Remove scripts, styles, headers, footers
            for noise in soup(["script", "style", "nav", "footer", "header", "aside"]):
                noise.extract()
            return soup.get_text(separator=" ")
    except Exception:
        return ""

async def reevaluate_all_jobs(status_filter="new", dry_run=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    query = "SELECT id, title, company, url, site_source, location, country, score FROM jobs"
    params = []
    if status_filter:
        query += " WHERE status = ?"
        params.append(status_filter)
    query += " ORDER BY id DESC"
    
    cur.execute(query, params)
    jobs = [dict(r) for r in cur.fetchall()]
    
    print(f"[*] Found {len(jobs)} jobs with status='{status_filter}' to evaluate.")
    
    active_profile = get_active_profile()
    
    rejected_count = 0
    updated_count = 0
    reasons_summary = {}

    semaphore = asyncio.Semaphore(10)

    async def evaluate_single_job(session, job):
        nonlocal rejected_count, updated_count
        job_id = job["id"]
        title = job.get("title") or ""
        company = job.get("company") or ""
        url = job.get("url") or ""
        location = job.get("location") or ""
        country = job.get("country") or ""

        async with semaphore:
            jd_text = await fetch_jd_text(session, url)

        filter_res = score_job(
            jd_text=jd_text,
            title=title,
            location=location,
            country=country,
            company=company,
            url=url,
            profile_data=active_profile
        )

        is_disq = filter_res.get("is_disqualified", False)
        reasons = filter_res.get("disqualified_by", [])
        new_score = filter_res.get("score", job.get("score", 0))
        detected_country = filter_res.get("detected_country")

        if is_disq:
            rejected_count += 1
            reason_str = "; ".join(reasons)
            print(f"  [-] REJECTING Job {job_id}: '{title}' at '{company}' (Reason: {reason_str})")
            for r in reasons:
                reasons_summary[r] = reasons_summary.get(r, 0) + 1
            if not dry_run:
                cur.execute("UPDATE jobs SET status = 'rejected', score = ? WHERE id = ?", (new_score, job_id))
        else:
            updated_count += 1
            print(f"  [+] QUALIFIED Job {job_id}: '{title}' at '{company}' (Score: {new_score}%, Country: {detected_country})")
            if not dry_run:
                cur.execute(
                    "UPDATE jobs SET score = ?, country = ? WHERE id = ?",
                    (new_score, detected_country or country, job_id)
                )

    async with aiohttp.ClientSession() as session:
        tasks = [evaluate_single_job(session, j) for j in jobs]
        await asyncio.gather(*tasks)

    if not dry_run:
        conn.commit()
    conn.close()

    print("\n" + "=" * 50)
    print(f"[*] Rescore & Cleanse Complete (dry_run={dry_run}):")
    print(f"    - Evaluated: {len(jobs)}")
    print(f"    - Qualified: {updated_count}")
    print(f"    - Rejected:  {rejected_count}")
    print("\nRejection Reasons Breakdown:")
    for reason, count in sorted(reasons_summary.items(), key=lambda x: x[1], reverse=True):
        print(f"    - [{count}] {reason}")
    print("=" * 50)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Cleanse and rescore jobs in job_tracker.db")
    parser.add_argument("--status", default="new", help="Status filter (default: 'new', use '' for all)")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run without updating DB")
    args = parser.parse_args()

    asyncio.run(reevaluate_all_jobs(status_filter=args.status, dry_run=args.dry_run))

if __name__ == "__main__":
    main()
