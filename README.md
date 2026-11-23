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
- **Automated Cloud Crawler & SMTP Email Packages**: Runs 3x daily on GitHub Actions (7 AM / 1 PM / 9 PM PST) with GitHub Actions Cache deduplication, public-repo-safe secret injection, multi-profile delta packaging (`.zip` with JSON/CSV/Markdown), SMTP email digests, and 1-command local SQLite import (`scripts/import_package.py`).
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

# CI-friendly fast mode (ATS APIs + Job Boards, skips Phase 1b company crawl) with a 20-minute soft budget
python scripts/auto_scour.py --mode fast --time-budget 20

# Headless-browser-free ATS API mode targeting a specific profile
python scripts/auto_scour.py --mode ats-only --profile "Default Profile"
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

---

## Automated Scheduled Cloud Crawler & SMTP Email Packages

TalentScout includes a **zero-infrastructure scheduled pipeline** (`.github/workflows/scheduled-scour.yml`) designed specifically for **public repositories** so you can run the crawler automatically in the cloud, deduplicate against prior runs, and receive portable `.zip` job packages via SMTP email.

### Architectural Decisions

| Decision | Choice | Why |
| --- | --- | --- |
| **Repo Visibility & PII Hygiene** | **GitHub Actions Secrets only** (never committed) | TalentScout is a public repo (serving GitHub Pages). SMTP credentials, recipient emails, and custom multi-profile definitions are injected strictly at runtime via environment secrets. Public workflow logs automatically mask recipient addresses (`t***@domain.com`), and only non-PII `scour_telemetry.json` is uploaded as a workflow artifact. |
| **State & Deduplication Persistence** | **GitHub Actions Cache (`job_tracker.db`)** | Avoids committing binary SQLite databases or personal job history to a public branch while requiring zero external databases. Before saving the cache, the workflow executes `PRAGMA wal_checkpoint(TRUNCATE)` so WAL writes are flushed into `job_tracker.db`. Because runs occur 3x/day, GitHub's 7-day cache eviction window is continuously refreshed. |
| **Delta-Only Delivery** | **SQLite `profile_deliveries` table** | Tracks `(profile_id, job_id)` pairs idempotently and only records delivery *after* SMTP succeeds. Each email contains strictly newly discovered roles—never duplicates from prior runs—and failed SMTP attempts retry cleanly on the next run. |
| **Crawler Runtime Scope** | **`fast` mode + 20m soft budget** | Datacenter IPs face stricter bot walls and CI runners have finite job budgets. Each scheduled run executes DreamworkHQ's direct API (`ingest_dreamwork.py`) plus `auto_scour.py --mode fast --time-budget 20` (Phase 0 HTTP ATS APIs + Phase 1a job boards, skipping the 13,000+ direct company scrape in Phase 1b). You can switch to `ats-only` (no browser) or `full` via manual dispatch. |
| **Multi-Profile Delivery** | **Single-user default + multi-profile JSON** | Works out-of-the-box for one user with a single `RECIPIENT_EMAIL` secret, and scales to N profile users via `TALENTSCOUT_PROFILES_JSON`—each receiving their own independently scored and deduplicated `.zip` package. |
| **Email Transport** | **Python stdlib `smtplib` (SMTP)** | Zero third-party email SDK dependencies; supports STARTTLS (port `587`) and SSL/TLS (port `465`) with any standard mail provider (Gmail App Password, Fastmail, Outlook, custom SMTP). |

### Schedule (3x Daily, PST-Aligned)

Configured in `.github/workflows/scheduled-scour.yml` via `cron: '0 5,15,21 * * *'`:

| Run Window | Pacific Standard Time (PST, UTC-8) | Pacific Daylight Time (PDT, UTC-7) | UTC Cron Hour |
| --- | --- | --- | --- |
| **Morning** | 7:00 AM PST | 8:00 AM PDT | `15:00 UTC` |
| **Midday** | 1:00 PM PST | 2:00 PM PDT | `21:00 UTC` |
| **Evening** | 9:00 PM PST | 10:00 PM PDT | `05:00 UTC` |

> **GitHub Actions Operational Notes:**
> - Scheduled (`cron`) workflows **only execute on the repository's default branch (`main`)**. Merge your feature branch into `main` to activate the schedule.
> - GitHub Actions cron timing can drift 5–20 minutes during peak UTC hours and automatically disables schedules after **60 days with no repository commits** (re-enable with one click in the Actions tab).
> - Use **Actions → TalentScout Scheduled Scour & Email Digest → Run workflow** (`workflow_dispatch`) to test immediately with `dry_run: true` or switch between `fast`, `ats-only`, and `full` modes.

### Configuring GitHub Actions Secrets

Go to **Repository Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret Name | Required | Example / Notes |
| --- | --- | --- |
| `SMTP_HOST` | Yes | `smtp.gmail.com` (Gmail), `smtp.fastmail.com`, etc. |
| `SMTP_PORT` | Optional | `587` (default, STARTTLS) or `465` (SSL) |
| `SMTP_USER` | Yes | Your SMTP login username / email address |
| `SMTP_PASS` | Yes | Provider **App Password** (for Gmail with 2FA, create a Google App Password rather than using your account password) |
| `SMTP_FROM` | Optional | Defaults to `SMTP_USER`; override if sending from an alias |
| `SMTP_SECURITY` | Optional | `starttls` (default for 587) or `ssl` (auto-selected for 465) |
| `RECIPIENT_EMAIL` | Single-user | Destination email for the default profile |
| `DELIVERY_MIN_SCORE` | Optional | Integer cutoff `0–100` (defaults to `40`) |
| `DELIVERY_MAX_JOBS` | Optional | Max jobs per email package (defaults to `50`) |
| `TALENTSCOUT_PROFILES_JSON` | Multi-profile | Optional JSON array defining 1+ private profiles & recipients (overrides `RECIPIENT_EMAIL` when enabled profiles are present) |

**Example `TALENTSCOUT_PROFILES_JSON` secret (for multiple profile users):**
```json
[
  {
    "name": "Default Profile",
    "recipient_email": "thomas@example.com",
    "delivery": { "enabled": true, "min_score": 45, "max_jobs": 50 }
  },
  {
    "name": "Backend Friend",
    "recipient_email": "friend@example.com",
    "delivery": { "enabled": true, "min_score": 50, "max_jobs": 30 },
    "search": { "default_terms": ["Backend Engineer", "Go Developer"] },
    "scoring": { "core_tech": ["Go", "PostgreSQL", "Kubernetes", "Docker"] }
  }
]
```

### Email Package Contents & Local Import

Every qualifying run emails a readable HTML summary (top roles, score badges, matched skills, direct apply links) with a compact `.zip` package attached (`talentscout_<profile>_<timestamp>.zip`, auto-capped under 18 MB):
- `manifest.json` — Run ID, UTC timestamp, profile name, job count, and schema version
- `jobs_delta.json` — Full structured records (including descriptions when within attachment budget)
- `jobs_summary.csv` — Spreadsheet-ready table of roles
- `jobs_digest.md` — Markdown review table
- `scour_telemetry.json` — Crawl health, block counters, and rejection breakdown

To merge a received `.zip` package into your local TalentScout SQLite database (so you can immediately run local LLM resume tailoring on those roles):
```powershell
# Preview contents without modifying job_tracker.db
python scripts/import_package.py talentscout_default-profile_20261122_150000.zip --dry-run

# Import idempotently (existing URLs are skipped automatically)
python scripts/import_package.py talentscout_default-profile_20261122_150000.zip
```

---

### Implementing This on Non-GitHub Repository Managers (Portability Guide)

All scheduling, secret syncing, crawling, packaging, and SMTP delivery logic lives in **platform-agnostic Python scripts** (`scripts/ci_bootstrap.py`, `scripts/auto_scour.py`, `scripts/package_and_email.py`, `scripts/import_package.py`) configured purely via standard environment variables. GitHub Actions is only a thin YAML wrapper around four universal commands:

```bash
python scripts/ci_bootstrap.py
python scripts/ingest_dreamwork.py --profile-id 1 --days 2 --limit 25 --no-md
python scripts/auto_scour.py --profile 1 --mode fast --time-budget 20
python scripts/package_and_email.py --out-dir logs/packages
```

To run this same pipeline on **non-GitHub repository hosts or self-hosted infrastructure**, account for these four pillars:

| Platform / Manager | 1. Scheduler | 2. Secret Injection | 3. SQLite State Persistence (`job_tracker.db`) | 4. Browser Runtime Notes |
| --- | --- | --- | --- | --- |
| **GitLab CI/CD** | *Build → Pipeline schedules* (`0 5,15,21 * * *`, set TZ directly to `America/Los_Angeles` if desired) | *Settings → CI/CD → Variables* (mark **Masked** & **Protected**; use File type for `TALENTSCOUT_PROFILES_JSON`) | `.gitlab-ci.yml` `cache:` key scoped to `job_tracker.db` (or GitLab Generic Package Registry for longer retention); run `PRAGMA wal_checkpoint(TRUNCATE)` in `after_script` | Use `mcr.microsoft.com/playwright/python:v1.58.0-noble` Docker image to skip Chromium install overhead |
| **Bitbucket Pipelines** | *Pipelines → Schedules* (hourly/daily/weekly UI; create 3 daily schedules) | *Repository settings → Repository variables* (mark **Secured**) | Custom pipeline `caches:` entry (note Bitbucket caches expire after 7 days and don't overwrite an existing key—rotate key or sync `job_tracker.db` to S3/R2/Backblaze B2) | Increase step `size: 2x` (8 GB RAM) if running Playwright Chromium, or use `--mode ats-only` on `1x` |
| **Gitea / Forgejo Actions** | `.gitea/workflows/` or `.forgejo/workflows/` — nearly 1:1 compatible with `.github/workflows/scheduled-scour.yml` | *Settings → Actions → Secrets* (same secret names) | Self-hosted runners can bind-mount a persistent host directory (`-v /srv/talentscout/data:/data`) for zero-eviction SQLite storage | Pre-install Chromium on the runner image or run with `--mode ats-only` for lightweight containers |
| **Azure DevOps Pipelines** | `schedules:` block in `azure-pipelines.yml` (`always: true` so it runs even without new commits) | *Pipelines → Library → Variable groups* (lock secret variables) | `Cache@2` task or Azure Blob Storage sync before/after run | Pin `ubuntu-24.04` hosted agents so `playwright install chromium --with-deps` maps cleanly to `libasound2t64` |
| **Self-Hosted (`cron` / `systemd` / Windows Task Scheduler)** | Crontab (`0 7,13,21 * * *` in local TZ — automatically handles PST/PDT!) or Windows Task Scheduler | Root/user-only `.env` file (`chmod 600 .env`) loaded before running the scripts | **Zero cache needed** — `job_tracker.db` persists natively on disk alongside your local dashboard | Runs from your residential IP (significantly fewer Cloudflare/job-board blocks than cloud datacenter IPs) |

**Four Universal Gotchas for Any Non-GitHub Setup:**
1. **Always checkpoint SQLite WAL before persisting state**: TalentScout enables `PRAGMA journal_mode=WAL`. If your CI caches or uploads only `job_tracker.db` without running `PRAGMA wal_checkpoint(TRUNCATE)`, recent `jobs` and `profile_deliveries` rows can remain stranded in `job_tracker.db-wal`.
2. **Prevent overlapping runs**: Configure concurrency/mutex locking (e.g., `resource_group:` in GitLab, `flock` in Linux `cron`) so two scheduled runs never overwrite each other's `job_tracker.db`.
3. **Never expose artifacts publicly on public repos**: Keep `.zip` packages off public job artifacts—deliver them privately over SMTP and only retain sanitized telemetry JSON if needed.
4. **Watch datacenter IP throttling**: Cloud runners (AWS/Azure/GCP) see higher 403/Turnstile rates on LinkedIn/Indeed/Glassdoor than residential IPs. Pair `--mode fast` or `--mode ats-only` with `--time-budget 20` so runs stay fast, reliable, and well within CI minute quotas.

