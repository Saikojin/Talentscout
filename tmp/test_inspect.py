import sqlite3
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.profile import get_active_profile
from scripts.scorer import score_job
from scripts.location_utils import evaluate_job_location

conn = sqlite3.connect('job_tracker.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT id, title, company, location, country, url, site_source, score FROM jobs WHERE status = 'new'")
rows = [dict(r) for r in cur.fetchall()]

print(f"Total new jobs: {len(rows)}")
for r in rows:
    print(f"ID: {r['id']} | Site: {r['site_source']} | Score: {r['score']}")
    print(f"  Title: {r['title']}")
    print(f"  Company: {r['company']}")
    print(f"  Location in DB: {r['location']}")
    print(f"  Country in DB: {r['country']}")
    print(f"  URL: {r['url']}")
    print()
