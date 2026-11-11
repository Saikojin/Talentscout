# Task Checklist: Layoffs & Hires (layoffsandhires.com) Integration into Auto Scour

## Intent Understanding
> **Core Objective:** Integrate `https://layoffsandhires.com/` into TalentScout's automated scouring engine (`scripts/auto_scour.py`) and company discovery pipelines. Support dynamic single-page application (SPA) searching by typing terms into the interactive search box, auto-clicking the expand button to uncover all matching hiring companies, extracting company career/job pages pre-filtered for that query, and persisting company and selector configurations in `site_selectors.json`, `job_search_sites.json`, `base_companies.json`, and SQLite `job_tracker.db`.

---

## Task DAG & Verification Contracts

- [x] **Task 1: Add Dynamic Search Input & Expansion Support to `scripts/auto_scour.py`**
  - [GATE: QA]
  - Priority: 0
  - Dependencies: None
  - Design additions:
    - In `scripts/auto_scour.py` (`scrape_site`):
      - Support `search_input_selector` (`input[type='search'], input[placeholder*='Search']`).
      - Dynamically types `search_term` into the search box on client-rendered SPA sites.
      - Support `expand_button_selector` (`button.matches-more`). Automatically clicks the "Show X more" button and extracts all 60 expanded matching company career links.
      - Support `is_career_directory` for proper role title formatting (`{search_term} ({job_count})`) and career portal URL verification.
  - **Verification command:** `python -m unittest scripts/test_layoffs_and_hires.py` (PASS)

- [x] **Task 2: Support Dynamic Search Input & Expansion in `scripts/audit_selectors.py`**
  - [GATE: QA]
  - Priority: 0
  - Dependencies: None
  - Design additions:
    - In `scripts/audit_selectors.py` (`audit_single_site`):
      - If `search_input_selector` is defined, automatically fills input with `keyword`.
      - If `expand_button_selector` is defined, clicks to expand results to 60 cards.
      - Career portal URLs on known ATS platforms (Workday, Greenhouse, Lever, Ashby, Workable) verified through `is_likely_job_url(..., allow_career_portals=True)`.
  - **Verification command:** `python scripts/audit_selectors.py --site "Layoffs & Hires"` (PASS: 60/60 cards extracted)

- [x] **Task 3: Configure `Layoffs & Hires` in `site_selectors.json`, `job_search_sites.json`, and SQLite DB**
  - [GATE: QA]
  - Priority: 1
  - Dependencies: Task 1, Task 2
  - Config details:
    - `search_url`: `"https://layoffsandhires.com/"`
    - `search_input_selector`: `"input[type='search'], input[placeholder*='Search']"`
    - `expand_button_selector`: `"button.matches-more"`
    - `job_card_selector`: `"section.matches ol.matches-list li"`
    - `title_selector`: `"span.matches-name"`
    - `company_selector`: `"span.matches-name"`
    - `job_url_selector`: `"a"`
    - `is_career_directory`: `True`
  - Synced to SQLite `sites` and `search_configs` tables. Added column migrations for `search_input_selector`, `expand_button_selector`, and `is_career_directory`.
  - **Verification command:** `python tmp/verify_db.py` (PASS)

- [x] **Task 4: Build Standalone Ingestor & Harvester (`scripts/ingest_layoffs_and_hires.py`)**
  - [GATE: QA]
  - Priority: 1
  - Dependencies: Task 3
  - Features:
    - Pulls `https://layoffsandhires.com/search/companies.json` and ingests 3,462 companies into `base_companies.json` and SQLite `companies` table.
    - Classifies ATS platforms (`workday`, `greenhouse`, `ashby`, `lever`, `workable`, `smartrecruiters`, `bamboohr`, etc.).
    - Queries inverted index `/search/t/{prefix}.json` for instant sub-second lookup of companies hiring for any keyword (e.g. 443 companies hiring for "QA").
    - CLI support for `--sync-all`, `--sync-config`, `--sync-companies`, `--search "<term>"`.
  - **Verification command:** `python scripts/ingest_layoffs_and_hires.py --search "QA" --limit 10` (PASS: 443 hiring companies found)

- [x] **Task 5: End-to-End Test Suite Pass & Living Documentation Update (`CONTEXT.md`, `README.md`)**
  - [GATE: QA]
  - Priority: 2
  - Dependencies: Task 1, Task 2, Task 3, Task 4
  - Run full test suite: `python -m unittest discover -s scripts -p "test_*.py"`.
  - Update `README.md` and `CONTEXT.md` with Layoffs & Hires configuration and usage.
  - **Verification command:** `python -m unittest discover -s scripts -p "test_*.py"` (81/81 passing)

---

## Seikojin QA Gatekeeping Checklist
- [x] `auto_scour.py` successfully navigates, fills search input, clicks expand button, and extracts 59-60 cards from `https://layoffsandhires.com/`.
- [x] `scripts/audit_selectors.py --site "Layoffs & Hires"` reports PASS with 60 cards extracted.
- [x] 3,462 companies from `layoffsandhires.com` ingested into `base_companies.json` and `job_tracker.db` with ATS classification.
- [x] 100% test pass rate across new and existing tests (`test_*.py`) — 81/81 tests passing.
