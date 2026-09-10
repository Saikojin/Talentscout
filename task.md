# Task Checklist: Service Port Isolation & Scour Rotation Restoration

- [x] **Task 1: Clean Blacklist & Restore Scour Rotation (`blacklist.json`)**
  - [x] Purge the 3,273 false-positive auto-blacklisted entries from `blacklist.json`, restoring it to the canonical 15 verified entries.
  - [x] Verify that all 10,891 companies in `job_tracker.db` and search configs are active in the rotation and no longer skipped upfront.
  - [x] Verification command: `python -c "import json; bl=json.load(open('blacklist.json')); print('Blacklist size:', len(bl))"`

- [x] **Task 2: Fix Aggressive DNS & Auto-Blacklisting Bug in Crawler (`scripts/auto_scour.py`)**
  - [x] Remove global `socket.setdefaulttimeout(2.0)` mutation in `_check_dns_sync` that caused spurious DNS failures across coroutines.
  - [x] Remove destructive `auto_blacklist()` calls on general navigation timeouts, network exceptions, or single DNS check failures in `is_domain_reachable`, `scrape_company`, and `scrape_site`.
  - [x] Make domain reachability checks resilient with proper logging without permanently blacklisting sites.
  - [x] Verification command: Run mock scour or test reachability check on sample domains (e.g., `adobe.com`, `ea.com`, `3m.com`).

- [x] **Task 3: Service Port Separation & Conflict Resolution (`scripts/dashboard_server.py`, `scripts/resume_server.py`)**
  - [x] Ensure `scripts/dashboard_server.py` runs on dedicated Port **8088** (supporting `PORT` / `DASHBOARD_PORT` env vars).
  - [x] Update `scripts/resume_server.py` to run on dedicated Port **8085** (avoiding port 8000 collision with LLM server and port 8088 with Dashboard).
  - [x] Ensure all frontend client templates (`dashboard.html`, `dashboard/profile_editor.html`, `dashboard/manage_crawlers.html`, `dashboard/resume_scanner.html`) use consistent API routes and distinct ports.
  - [x] Verification command: Start dashboard server and resume server on their respective ports to verify no port collision.

- [x] **Task 4: Update Process Management Scripts (`start.bat`, `stop.bat`)**
  - [x] Update `start.bat` with clear port overview (Dashboard: 8088, LLM: 8000/8080, Resume: 8085, MCP: 3001).
  - [x] Update `stop.bat` to kill processes listening on all configured ports (8088, 8085, 8000, 8080, 3001).
  - [x] Verification command: Dry run / test script syntax and port list.

- [x] **Task 5: Update Living Context & Documentation (`CONTEXT.md`, `README.md`, `docs/manual_job_search.md`)**
  - [x] Document all assigned service ports and separation in `CONTEXT.md` and `README.md`.
  - [x] Document crawler troubleshooting and blacklist maintenance in `docs/manual_job_search.md`.
  - [x] Verification: Full review of all markdown docs and link checks.
