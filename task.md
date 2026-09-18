# Task Checklist: Location Integrity, Scour Disqualification & Dashboard Cleanliness

- [x] **Task 1: Fix Site Table Schema & Selectors (`scripts/database.py`, `job_tracker.db`, `site_selectors.json`)**
  - [x] Add `location_selector` column to `sites` table in `scripts/database.py` and run schema migration on `job_tracker.db`.
  - [x] Populate correct `location_selector` strings for all sites (Dice, Glassdoor, SimplyHired, CareerBuilder, Monster, GameJobs, BuiltIn, LinkedIn, Indeed, etc.) from `site_selectors.json`.
  - [x] Verification command: `python -c "import sqlite3; conn = sqlite3.connect('job_tracker.db'); cur = conn.cursor(); cur.execute('SELECT name, location_selector FROM sites'); print(cur.fetchall())"`

- [x] **Task 2: Eliminate Search Query Fallback Location Corruption (`scripts/auto_scour.py`)**
  - [x] Modify `scrape_site()` so it NEVER populates `job["location"]` with the search query `location` variable when `card_location` is empty. If no card location is found, leave `location=""` or `None`.
  - [x] Ensure `process_discovered_job()` extracts/reconciles location from the fetched `jd_text` or ATS API payload rather than trusting search query strings.
  - [x] Verification command: Test running mock `scrape_site` on GameJobs and Dice to confirm `location` is not falsely stamped with "Seattle".

- [x] **Task 3: Harden Location & Country Evaluation (`scripts/location_utils.py`, `scripts/scorer.py`)**
  - [x] Synchronize `COUNTRY_CODES_MAP` and expand `FOREIGN_LOCATIONS_MAP` with complete international countries, territories, and major tech cities (including Pakistan, Qatar, UAE, Saudi Arabia, etc.).
  - [x] Refactor `is_remote_role()` to eliminate false positives on generic words like isolated `virtual` and `nationwide`, requiring clear remote-work phrases (`remote`, `work from home`, `wfh`, `telecommute`, `virtual role`).
  - [x] Fix `evaluate_job_location()` so that `is_target_location` only tests the true location header and actual location statements, NOT pre-pending metadata that bypasses JD foreign country / out-of-state checks.
  - [x] Close the fallthrough loophole in Step 6: When `require_local_or_remote` is `True`, any job that is NOT explicitly confirmed as a target location (WA / Seattle metro) and NOT confirmed US-remote MUST be disqualified.
  - [x] Ensure `detected_country` only returns `"United States"` when genuinely verified, not as a blanket default fallback for unvetted roles.
  - [x] Verification command: Run `pytest` or dedicated test script (`scripts/test_location_profiles.py` and `tmp/test_location_hardening.py`) covering Riot Games (Singapore), Dice (Indiana), Veeam (Pakistan/Qatar), Evolution (NJ), and Shield AI (Wichita).

- [x] **Task 4: Database Cleanse & Rescoring Utility (`scripts/cleanup_invalid_jobs.py` / `scripts/database.py`)**
  - [x] Create a migration/rescore script that evaluates all existing "new" and active jobs in `job_tracker.db` against the hardened scoring engine, auto-rejecting or purging false-positive entries.
  - [x] Verification command: `python scripts/cleanup_invalid_jobs.py --dry-run` followed by live cleanup.

- [x] **Task 5: Documentation & Living Context Update (`CONTEXT.md`, `README.md`)**
  - [x] Update `CONTEXT.md` to document the location resolution architecture, multi-source provenance, and safety nets.
  - [x] Update test memory and walkthrough documentation.
