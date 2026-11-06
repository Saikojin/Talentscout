# Task Checklist: DOM Selector Drift Detection, Telemetry & Self-Healing

## Intent Understanding
> **Core Objective:** Eliminate silent crawler failures caused by DOM Selector Drift (where sites update HTML layouts, leading to zero job cards or fallback to search URLs). Instrument granular drift telemetry into `ScourTelemetry`, build an offline selector auditor tool (`scripts/audit_selectors.py`), implement smart fallback heuristic extraction to rescue broken selectors, stop search-URL queue poisoning (125 instances in latest run), and repair drifted selectors in `site_selectors.json`.

---

## Task DAG & Verification Contracts

- [x] **Task 1: Selector Drift Telemetry in `ScourTelemetry` (`scripts/scour_telemetry.py`, `scripts/test_scour_telemetry.py`)**
  - [GATE: QA]
  - Priority: 0
  - Dependencies: None
  - Design additions to `scripts/scour_telemetry.py`:
    - `record_selector_drift(site, url, drift_type, selector, details, rescued=False, rescued_count=0)`:
      - `drift_type` in `["card_selector", "link_selector", "title_selector", "company_selector"]`.
      - Aggregates drift counts by type and tracks rescued vs hard failures.
    - Update `format_summary()`:
      - Add dedicated `[!] DOM SELECTOR DRIFT DETECTED` section showing breakdown of broken selectors.
    - Update `to_dict()` and export in `logs/scour_summary_latest.json`.
  - **Verification command:** `python -m unittest scripts/test_scour_telemetry.py` (11/11 passing)

- [x] **Task 2: Heuristic Smart Fallback Engine (`scripts/selector_heuristics.py`, `scripts/test_selector_heuristics.py`)**
  - [GATE: QA]
  - Priority: 0
  - Dependencies: None
  - Design `scripts/selector_heuristics.py`:
    - `find_fallback_cards(page_or_locator)`: inspects semantic elements (`article`, `li[data-testid*="job"]`, `div[data-testid*="job-card"]`, `div[data-job-id]`, `div[class*="job"]`).
    - `extract_fallback_title(card)`: inspects headings `h1, h2, h3, h4`, `a[class*="title"]`, `[data-testid*="title"]`, `strong`.
    - `extract_fallback_link(card, base_url)`: searches anchors inside card for job paths (`/job/`, `/jobs/`, `/viewjob`, `/posting/`, `/position/`, `jobid=`), validating against `is_non_job_url` and rejecting `base_url`.
  - **Verification command:** `python -m unittest scripts/test_selector_heuristics.py` (10/10 passing)

- [x] **Task 3: Integrate Drift Telemetry & Fallbacks into Scour Loop (`scripts/auto_scour.py`, `scripts/test_scour_selector_drift.py`)**
  - [GATE: QA]
  - Priority: 1
  - Dependencies: Task 1, Task 2
  - In `auto_scour.py`:
    - In `scrape_site`:
      - When `wait_for_selector(card_sel)` times out or yields 0 cards on an unblocked page (HTTP 200, no challenge):
        - Call `find_fallback_cards(page)`.
        - If rescued: record telemetry `card_selector` drift with `rescued=True` and parse the cards.
        - If 0 cards: record `card_selector` drift with `rescued=False` and exit cleanly.
      - In card loop:
        - If link extraction fails: attempt `extract_fallback_link()`. If still none, **do NOT** fall back to search URL—record `link_selector` drift and skip the card.
        - If title is `"Unknown Title"`: attempt `extract_fallback_title()`. If still none, record `title_selector` drift.
    - In `scrape_company`:
      - If `card_sel` times out, fall back to smart link scraper and record `card_selector` drift instead of aborting with `[]`.
  - **Verification command:** `python -m unittest scripts/test_scour_selector_drift.py` (3/3 passing)

- [x] **Task 4: Standalone Offline Selector Auditor CLI (`scripts/audit_selectors.py`, `scripts/test_audit_selectors.py`)**
  - [GATE: QA]
  - Priority: 1
  - Dependencies: None
  - Design `scripts/audit_selectors.py`:
    - Probe search URLs defined in `site_selectors.json` with Playwright stealth context.
    - CLI flags: `--site <Name>`, `--all`, `--drift-only`, `--fix`.
    - Validates presence of card selector, title selector, job URL selector, company selector.
    - Outputs diagnostic table: extracted cards, sample title, sample URL, and status (`OK`, `DRIFT`, `BLOCKED`).
  - **Verification command:** `python -m unittest scripts/test_audit_selectors.py` (3/3 passing)

- [x] **Task 5: Repair Top Drifted Selectors in `site_selectors.json`**
  - [GATE: QA]
  - Priority: 2
  - Dependencies: Task 4
  - Audit and update broken selectors for top impacted sites:
    - ZipRecruiter (PASS: 20 cards extracted).
    - Google Careers (PASS: 20 cards extracted, direct URLs resolved).
    - Dice (PASS: 8 cards extracted, direct URLs resolved).
    - Glassdoor (PASS: 16 cards extracted, job listing URLs resolved).
    - Microsoft Careers (PASS: 45 cards extracted, direct `/careers/job/` URLs resolved).
  - **Verification command:** `python scripts/audit_selectors.py` (6/6 passing)

- [x] **Task 6: End-to-End Test Suite Pass & Living Documentation Update (`CONTEXT.md`, `README.md`)**
  - [GATE: QA]
  - Priority: 2
  - Dependencies: Task 3, Task 5
  - Run full test suite: `python -m unittest discover -s scripts -p "test_*.py"`.
  - Update `README.md` and `CONTEXT.md` with selector drift metrics, fallback architecture, and `audit_selectors.py` usage.
  - **Verification command:** `python -m unittest discover -s scripts -p "test_*.py"` (77/77 passing)

---

## Seikojin QA Gatekeeping Checklist
- [x] Zero search URLs queued as Job Descriptions in Phase 2.
- [x] 100% test pass rate across new and existing tests (`test_*.py`) — 77/77 tests passing.
- [x] `logs/scour_summary_latest.json` exposes structured `selector_drifts` and `drift_stats`.
- [x] Terminal summary table displays high-density `DOM SELECTOR DRIFT DETECTED` metrics.
- [x] `scripts/audit_selectors.py` can audit single or multiple sites cleanly with stealth browser contexts.
