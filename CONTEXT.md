# TalentScout — Project Context

> **Living context document.** Future agent sessions should read this file first.
> Project root: `D:\DevWorkspace\TalentScout`

---

## What Is TalentScout?

TalentScout is a **Python-based automated job scraping and tracking system**. Its core features:

- **Multi-site scraping** via Playwright (headless, JS-rendered)
- **Stealth Anti-Bot Evasion (`scripts/browser_stealth.py`)**: Zero-dependency evasion layer masking `navigator.webdriver`, injecting realistic plugins/languages, and waiting for silent Turnstile/CAPTCHA challenges to self-solve.
- **Per-Domain Rate Limiting & Circuit Breakers (`scripts/rate_limiter.py`)**: Concurrency ceilings (e.g. 1-tab for LinkedIn, Indeed, Glassdoor), randomized inter-request delay jitter (2.5s–4.0s), and automated 5-minute cooldown circuit breakers on HTTP 429.
- **Crawler Block Telemetry & Rejection Analytics (`scripts/scour_telemetry.py`)**: Captures HTTP status blocks (403, 429, 503), WAF challenges (Cloudflare Turnstile, CAPTCHA), and login-walls, outputting formatted terminal reports and `logs/scour_summary_latest.json`.
- **DOM Selector Drift Detection & Self-Healing (`scripts/selector_heuristics.py`)**: Tracks broken card, link, title, and company selectors. Automatically executes bounded semantic heuristics (`article`, `li[data-testid*='job']`) to rescue postings, while dropping link-less cards to prevent search URL queue poisoning.
- **Standalone Offline Selector Auditor (`scripts/audit_selectors.py`)**: Diagnostic CLI tool using stealth Playwright contexts to audit, benchmark, and verify selectors in `site_selectors.json`.
- **Deep Scour Engine (`scripts/scour_deep.py`)**: Page-N scouring ignoring page 1 results, with page capacity survey mode (`--detect-pages-only`).
- **Endpoint Health & Dead Domain Quarantine (`scripts/verify_site_health.py`)**: Sweeps all target URLs across configurations, resolves DNS health, and maintains `quarantined_domains.json`.
- **Skill-based filtering** using `base_skillset.json`
- **SQLite deduplication** via `job_tracker.db`
- **Dashboard output & scoring** to `dashboard.html` (`http://localhost:8088`) and `jobs_to_review.md`
- **1-Click Tailored Resume & Cover Letter Generator**: Generates custom Resumes and Cover Letters tailored to specific job cards.
- **Bundled Local LLM Engine (`llmworkbench/`)**: On-device GGUF inference (port 8000, worker 8080) with UI start/stop controls.
- **Resume Parser UI**: Integrated into Unified Dashboard (`http://localhost:8088/scanner`) with standalone fallback on port 8085.

### New: Resume-as-Code Sub-project

A new `resume/` subdirectory integrates a Node.js **resume-as-code engine**:
- Single source of truth: `resume/data/resume.json` (JSON Resume standard, extended with `tags` and 26-year career records for Thomas S. Snyder)
- Compiles to Markdown, HTML, PDF
- Exposes an **MCP server** (7 AI agent tools) at `http://localhost:3001/mcp`
- Exports ATS profiles for **Greenhouse** and **Workday**
- Powers a premium interactive **portfolio landing page** with a Focus Selector

---

## Tech Stack

| Layer | Technology | Port |
|---|---|---|
| Job scraping | Python 3.8+, Playwright, BeautifulSoup4 | N/A (CLI Engine) |
| Data storage | SQLite3 (`job_tracker.db`) | N/A (Local File) |
| Unified Web Server | FastAPI + Uvicorn | `:8088` |
| Local LLM Backend | FastAPI + Uvicorn + GGUF Engine | `:8000` (Worker `:8080`) |
| Standalone Parser | FastAPI + Uvicorn | `:8085` |
| MCP Server | TypeScript, `@modelcontextprotocol/sdk` | `:3001` |
| Resume data | JSON Resume standard (Node.js) | N/A |
| Resume compiler | Node.js ESM scripts + marked + puppeteer | N/A |
| Resume tests | Vitest (29/29 passing) | N/A |
| Landing page | Vanilla HTML/CSS/JS | N/A |

---

## Project Status

### Python Job Scraper & Tailoring Engine (active)
- ✅ Multi-site scraping with Playwright
- ✅ **Stealth Anti-Bot Provider (`scripts/browser_stealth.py`)**: Masks `navigator.webdriver`, injects realistic plugins/languages, and includes a transient challenge resolver to automatically pass silent Turnstile/Cloudflare challenges (eliminating ZipRecruiter/Indeed 403s).
- ✅ **Per-Domain Rate Limiter & Circuit Breakers (`scripts/rate_limiter.py`)**: Restricts sensitive domains (LinkedIn, Indeed, Glassdoor) to 1-tab concurrency and 2.5s–4.0s jitter delay, with an automatic 5-minute circuit breaker cooldown on HTTP 429.
- ✅ **Endpoint Health & Dead Domain Sweeper (`scripts/verify_site_health.py`)**: Non-blocking DNS auditor that identifies and quarantines dead domains into `quarantined_domains.json`, eliminating DNS / Unreachable errors from future scours.
- ✅ **DOM Selector Drift Detection & Heuristics (`scripts/selector_heuristics.py` & `scripts/scour_telemetry.py`)**: Detects and logs selector breakages in real-time. Probes semantic fallback selectors when classes drift and prevents search URL queue poisoning.
- ✅ **Offline Selector Auditor CLI (`scripts/audit_selectors.py`)**: Standalone tool that tests `site_selectors.json` entries with stealth contexts and outputs diagnostic audit reports.
- ✅ **Crawler Block Telemetry & Rejection Analytics (`scripts/scour_telemetry.py`)**: Intercepts HTTP status codes (`403`, `429`, `503`), bot shields (Cloudflare Turnstile, CAPTCHA, PerimeterX, DataDome), and authentication walls (e.g. LinkedIn `/login`). Outputs rich ASCII terminal summary and JSON telemetry logs in `logs/scour_summary_latest.json`.
- ✅ **Deep Scour & Pagination Engine (`scripts/scour_deep.py` & `scripts/pagination_utils.py`)**: Scours page N results with `--page N`, `--skip-page-one`, and survey mode `--detect-pages-only` to discover site page capacity.
- ✅ Dynamic Profile & Scoring Engine (`scripts/profile.py` + `scripts/scorer.py` + `scripts/location_utils.py`) with customizable weights, dynamic candidate location properties (`country`, `state`, `city`, `postal_code`), configurable search constraints (`allowed_countries`, `target_states`, `preferred_cities`, `allow_remote`, `require_local_or_remote`), 50-state detection, and city/state disambiguation (e.g. `Redmond, OR` vs `Redmond, WA`).
- ✅ **Location Integrity & Safety Nets**:
  - **No Search Query Fallback**: `auto_scour.py` never overwrites missing card locations with the search keyword (`Seattle`).
  - **Site Table Location Selectors**: `sites` table includes `location_selector` column, fully migrated in `job_tracker.db` and configurable via dashboard API.
  - **Strict Remote Phrase Matching**: Disallows single generic words (`virtual`, `nationwide`) from triggering false-positive US-remote classifications.
  - **Foreign Country & Out-of-State Safety Nets**: Extensive coverage in `FOREIGN_LOCATIONS_MAP` (Pakistan, Qatar, UAE, India, UK, Singapore, Latin America, etc.) and `US_MAJOR_CITIES` (Puget Sound tech corridor + major US metros).
  - **True JD Priority**: Pre-pended metadata cannot mask international or non-target physical locations found in the actual job description.
  - **Live Cleanse Utility**: `scripts/cleanup_invalid_jobs.py` re-evaluates database jobs against candidate profile constraints and purges/rejects disqualified jobs.
- ✅ 1-Click Tailored Resume & Cover Letter Generator (`scripts/tailor_engine.py` & `dashboard.html`)
- ✅ **DreamworkHQ Ingestor (`scripts/ingest_dreamwork.py`)**: Direct zero-npm connection to DreamworkHQ's public API for fast, ATS-direct job scraping, dynamic persona/profile-driven scoring, and SQLite deduplication.
- ✅ Bundled Local LLM inference engine (`llmworkbench/`) with UI start/stop controls
- ✅ SQLite deduplication and multi-profile persistence
- ✅ Dashboard and Profile Editor UI (`dashboard/profile_editor.html` on port 8088) with home residence & job search location controls, and Markdown output

### Resume-as-Code (`resume/`)
- ✅ `resume/data/resume.json` — Comprehensive 26-year career history for Thomas S. Snyder
- ✅ Schema validation pipeline (AJV, strict JSON Schema)
- ✅ Compiler: JSON → Markdown + HTML + PDF + DOCX
