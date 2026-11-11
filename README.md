# TalentScout

TalentScout is an automated agentic job scraper that utilizes Playwright to find, filter, and track relevant job postings across multiple job boards. It leverages search selectors and filtering keywords to narrow down job descriptions to ones that match your exact skill set and saves you from applying to duplicates by storing them in a local SQLite database.
> **Note:** The configuration files in this repository contain example data from the project creator. To use this scraper effectively, you must edit these configurations to suit your specific job requirements and selectors. Additionally, this project presumes the user has access to an AI assistant (or agent) to help automate actions beyond the code execution itself.

## Features

- **Multi-Site Scraping**: Scour multiple job boards by defining site selectors in a JSON file.
- **Stealth Anti-Bot Evasion**: Zero-dependency evasion layer (`scripts/browser_stealth.py`) masking `navigator.webdriver`, injecting realistic plugins/languages, and waiting for silent Turnstile/CAPTCHA challenges to self-solve.
- **Per-Domain Rate Limiting & Circuit Breakers**: Concurrency ceilings (e.g. 1-tab for LinkedIn, Indeed, Glassdoor), randomized inter-request delay jitter (2.5s–4.0s), and automated 5-minute cooldown circuit breakers on HTTP 429.
- **Crawler Block Telemetry**: Real-time detection and structured classification of HTTP blocks (`403 Forbidden`, `429 Rate Limited`, `503 Service Unavailable`), Cloudflare challenges / Turnstile, and forced authentication walls.
- **DOM Selector Drift Telemetry & Self-Healing**: Real-time detection of broken selectors, heuristic layout rescue (`scripts/selector_heuristics.py`), and protection against search URL queue poisoning.
- **Offline Selector Auditor**: Standalone CLI tool (`scripts/audit_selectors.py`) to benchmark and diagnose CSS selectors across `site_selectors.json`.
- **Deep Scour & Page Capacity Discovery**: Scour beyond page 1 using `--page N` or `scripts/scour_deep.py`, automatically detecting how many pages each site has available.
- **Endpoint Health & Dead Domain Quarantine**: Offline sweeper (`scripts/verify_site_health.py`) that audits DNS health across all target URLs and quarantines dead domains.
- **Rejection Breakdown & Blacklist Audit**: High-density ASCII summary tables and persistent JSON logs (`logs/scour_summary_latest.json`) reporting exact rejection reasons and pre-filtered blacklist stats.
- **Skill Filtering**: Define your skills and disqualified keywords to automatically reject bad fits before you even see them.
- **DreamworkHQ Direct Ingestion**: Fast, zero-npm job discovery via DreamworkHQ's public API (`scripts/ingest_dreamwork.py`). Extracts direct employer ATS links (Greenhouse, Lever, Workday, BambooHR, etc.) with pre-parsed tech stacks and full descriptions.
- **Layoffs & Hires (layoffsandhires.com) Integration**:
  - Interactive SPA search with dynamic input typing (`search_input_selector`) and results expansion (`expand_button_selector`) in `scripts/auto_scour.py`.
  - Ingestion tool (`scripts/ingest_layoffs_and_hires.py`) syncing 3,462+ hiring companies with ATS detection (Workday, Greenhouse, Ashby, Lever, Workable, etc.) into `base_companies.json` and SQLite `companies`.
  - Fast token search using `/search/t/{prefix}.json` inverted indices for instant offline company hiring discovery.
- **Dynamic Multi-Persona Support**: Automatically adapts to whichever candidate profile is active in SQLite or custom skillset JSON files (`--skillset`). Enables any profession (Engineering, Data Science, QA, Product, DevOps) to search and score jobs against their own criteria.
- **Local Database Tracking**: Uses a local SQLite database (`job_tracker.db`) to log scraped jobs and prevent re-evaluating the same URL twice.
- **Dashboard Output & Scoring**: Generates an integrated HTML dashboard (`http://localhost:8088`) and a Markdown list (`jobs_to_review.md`) with multi-axis scoring.
- **1-Click Tailored Resume & Cover Letter Generator**: Generate targeted resumes and cover letters for specific job postings directly from the dashboard tiles.
- **Bundled Local LLM Engine (`llmworkbench/`)**: On-device AI inference using your own downloaded `.gguf` models with start/stop management directly in the UI.

## Tech Stack & Dependencies

- **Python 3.8+**: Core language for all scripts and logic.
- **Playwright** (`playwright`): Used for headless, Javascript-rendered, async web scraping.
- **FastAPI & Uvicorn** (`fastapi`, `uvicorn`, `python-multipart`): Powers the dashboard server (:8088) and local LLM backend (:8000).
- **LLMWorkbench Engine**: On-device GGUF model loader supporting Gemma, LFM, Qwen, etc.
- **BeautifulSoup4** (`beautifulsoup4`): HTML parsing for the visual learner tool.
- **PyPDF & python-docx** (`pypdf`, `python-docx`): Extracts raw text from uploaded resumes.
- **SQLite3**: Built-in Python library used for the local `job_tracker.db` deduplication database.
- **Vanilla HTML/CSS/JS**: Used for the dashboard rendering, avoiding the need for heavy node/npm dependencies.

## Setup

1. **Install Requirements**:
   Ensure you have Python 3.8+ installed, and run:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Download Local GGUF Models (Optional for Local AI)**:
   Place any GGUF language model (e.g. `gemma-3-1B-it-QAT-Q4_0.gguf`) into `llmworkbench/models/`.
   - *Note:* Models are excluded from git by default to keep the repository lightweight.
   - You can download models from [Hugging Face](https://huggingface.co/models?search=gguf).

3. **Configuration**:
   - `site_selectors.json`: Contains the CSS selectors and search URL templates for the job boards you want to scrape.
   - `job_search_sites.json`: Represents individual active queries (e.g., job title and location) you wish to apply on specific boards.
   - `base_skillset.example.json`: Rename this to `base_skillset.json` and fill it with your own personal skills. Jobs that don't match your criteria or contain disqualified skills will be automatically rejected.

## Usage

### 1. Start the Dashboard & Local LLM
Start the dashboard server:
```powershell
python scripts/dashboard_server.py
```
Open your browser to `http://localhost:8088`.
- In the top navigation, you will see the **Local LLM Widget**.
- Select a downloaded `.gguf` model from the dropdown and click **▶️ Start LLM**.

### 2. Run the Job Scraper (Playwright & ATS Harvester)
To start scoring and filtering jobs across configured job boards:
```bash
python scripts/auto_scour.py
```

#### Scour CLI Flags
The scour engine supports pagination controls, capacity discovery, and non-destructive dry runs:
```powershell
# Scour target page 2 (defaults to max 1 page)
python scripts/auto_scour.py --page 2

# Skip page 1 results entirely and start from page 2
python scripts/auto_scour.py --skip-page-one

# Fast capacity audit: probe job boards to detect available page count and bot blocks without scraping full JDs
python scripts/auto_scour.py --detect-pages-only

# Dry run: score jobs and test filters without modifying SQLite or jobs_to_review.md
python scripts/auto_scour.py --dry-run
```

### 3. Deep Scour (Page N Discovery)
When you want to bypass first-page results and dig deeper into older listings or verify page capacity:
```powershell
# Scour page 2 by default (ignoring page 1 results)
python scripts/scour_deep.py

# Inspect page 3 directly
python scripts/scour_deep.py --page 3

# Survey how many pages each site has so you know how far deep you can go
python scripts/scour_deep.py --detect-pages-only

# Test deep scour without database writes
python scripts/scour_deep.py --page 2 --dry-run
```

### 4. DOM Selector Drift Detection & Offline Auditor
TalentScout actively monitors and guards against DOM Selector Drift (when job boards change layout classes or component trees):
- **Selector Drift Telemetry**: Tracks Hard Card Drift, Link Drift, Title Drift, and Company Drift directly into `ScourTelemetry` and persistent JSON reports (`logs/scour_summary_latest.json`).
- **Heuristic Smart Fallbacks (`scripts/selector_heuristics.py`)**: Automatically probes semantic HTML elements (`article`, `li[data-testid*='job']`, `div[data-testid*='job-card']`) to rescue job postings when brittle class names change.
- **Queue Poisoning Protection**: Discards cards lacking identifiable job links instead of falling back to search page URLs, eliminating redundant Phase 2 JD scrapes.
- **Offline Selector Auditor Tool (`scripts/audit_selectors.py`)**: Quickly benchmark and diagnose selectors across `site_selectors.json` without running a full scour:
```powershell
# Audit all default top platforms (LinkedIn, Indeed, BuiltIn, Dice, Glassdoor, ZipRecruiter)
python scripts/audit_selectors.py

# Audit a specific job board
python scripts/audit_selectors.py --site Dice
python scripts/audit_selectors.py --site "Microsoft Careers"
python scripts/audit_selectors.py --site "Google Careers"

# Export structured audit results to JSON
python scripts/audit_selectors.py --all --json-out logs/selector_audit.json
```

### 5. Crawler Block Telemetry & Rejection Analytics
At the end of every scour run (`auto_scour.py` and `scour_deep.py`), TalentScout outputs an ASCII summary table and saves detailed JSON telemetry to `logs/scour_summary_latest.json`:
- **Crawler Blocks & Bot Defenses**: Detects HTTP `403 Forbidden`, `429 Rate Limited`, `503 Service Unavailable`, Cloudflare challenges / Turnstile, and forced authentication redirects (e.g. LinkedIn `/login`).
- **DOM Selector Drift**: Reports broken selectors, rescued sites/jobs, and link-poisoning bypasses.
- **Throttle & Circuit Breaker Telemetry**: Reports active domain cooldowns and requests spared/bypassed.
- **Blacklist & Quarantine Telemetry**: Summarizes pre-filtered domains and blacklisted companies skipped upfront.
- **Rejection Breakdown**: Categorized rejection counts (`Location / Foreign Country`, `Disqualified Skill`, `Negative Title Keyword`, `Empty JD SafetyNet`, `Low Score`) with sample roles.
- **Page Capacity Discovered**: Reports the total number of pages and estimated job count detected per site.

### 6. Verify Endpoint Health & Quarantine Dead Domains
Sweep configured job boards and company career sites to identify dead endpoints (resolving DNS / Unreachable errors):
```powershell
# Scan all target domains and save unreachable endpoints to quarantined_domains.json
python scripts/verify_site_health.py

# Audit with custom concurrency and strict timeout
python scripts/verify_site_health.py --timeout 3.0 --concurrency 40

# Prune verified dead companies from base_companies.json (creates .bak backup)
python scripts/verify_site_health.py --prune-dead-domains
```

### 7. Fast Job Discovery with DreamworkHQ (Zero-NPM Direct API)
Quickly harvest and score fresh roles directly from DreamworkHQ's public API without launching browser instances or installing npm packages:

```powershell
# Ingest jobs using active database profile defaults
python scripts/ingest_dreamwork.py

# Query custom terms or remote positions
python scripts/ingest_dreamwork.py --terms "Full Stack Developer, Python Engineer" --work-type remote

# Run for a different candidate's skillset file
python scripts/ingest_dreamwork.py --skillset path/to/candidate_skillset.json

# Preview and score without modifying the database or markdown review list
python scripts/ingest_dreamwork.py --dry-run --limit 10

# Adjust posting age window or score threshold cutoff
python scripts/ingest_dreamwork.py --days 7 --min-score 50 --limit 30
```

### 8. Generate 1-Click Tailored Resumes & Cover Letters
In the Dashboard (`http://localhost:8088`):
1. Click **✨ Tailor Resume & Cover Letter** on any job tile.
2. The local LLM will synthesize a tailored resume with CAR/STAR bullet points and a matching cover letter.
3. The interactive viewer will pop open with 1-click **Copy to Clipboard** and saved files in `tailored_outputs/<Company_Role>/`.
