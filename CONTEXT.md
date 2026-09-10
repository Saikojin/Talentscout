# TalentScout — Project Context

> **Living context document.** Future agent sessions should read this file first.
> Project root: `D:\DevWorkspace\TalentScout`

---

## What Is TalentScout?

TalentScout is a **Python-based automated job scraping and tracking system**. Its core features:

- **Multi-site scraping** via Playwright (headless, JS-rendered)
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
- ✅ Profile & Scoring Engine (`scripts/profile.py` + `scripts/scorer.py`) with customizable weights
- ✅ 1-Click Tailored Resume & Cover Letter Generator (`scripts/tailor_engine.py` & `dashboard.html`)
- ✅ Bundled Local LLM inference engine (`llmworkbench/`) with UI start/stop controls
- ✅ SQLite deduplication and profile persistence
- ✅ Dashboard and Profile Editor UI (`dashboard/profile_editor.html` on port 8088) and Markdown output

### Resume-as-Code (`resume/`)
- ✅ `resume/data/resume.json` — Comprehensive 26-year career history for Thomas S. Snyder
- ✅ Schema validation pipeline (AJV, strict JSON Schema)
- ✅ Compiler: JSON → Markdown + HTML + PDF + DOCX
- ✅ 29/29 tests passing (schema matrix + compiler integrity)
- ✅ MCP server (7 tools, stdio + HTTP transports)
- ✅ ATS adapters: Greenhouse + Workday
- ✅ Premium landing page with Focus Selector and "Plug into MCP" button

---

## Open Items

- [ ] **Replace placeholder data** in `resume/data/resume.json` with real user data
- [ ] Deploy `resume/web/` as a public static site (GitHub Pages / Vercel / Netlify)
- [ ] Register MCP server in Claude Desktop or Cursor config
- [ ] SpacetimeDB integration — build/test history storage (from project vision)
- [ ] DOCX export (pandoc-based)
- [ ] `--watch` mode for live-reload editing

---

## Key Files

| File | Purpose |
|---|---|
| `scripts/auto_scour.py` | Main job scraper entry point |
| `base_skillset.json` | Your skills for job filtering |
| `job_tracker.db` | SQLite deduplication DB |
| `dashboard.html` | Job scraper visual dashboard |
| `start.bat` / `stop.bat` | Resume parser server control |
| `resume/data/resume.json` | **Edit this** — your professional identity |
| `resume/compiler/validate.js` | Validate resume data |
| `resume/compiler/build.js` | Compile to MD + HTML + PDF |
| `resume/mcp-server/src/index.ts` | MCP server (7 agent tools) |
| `resume/web/index.html` | Portfolio landing page |
| `resume/docs/project_vision.md` | Master Vision document |
| `resume/docs/conversation_history.md` | Origin session summary + open items |

---

## Quick Commands

```powershell
# From D:\DevWorkspace\TalentScout

# --- Python Job Scraper & Unified Server ---
python scripts/auto_scour.py        # Run job scraper
.\start.bat                          # Start Unified Dashboard Server (localhost:8088)
.\stop.bat                           # Stop TalentScout services (8088, 8085, 8000, 8080, 3001)

# --- Resume Engine (from resume/) ---
cd resume
node compiler/validate.js            # Validate resume.json
node compiler/build.js               # Build MD + HTML
node compiler/build.js --pdf         # Build + PDF
node compiler/adapters/greenhouse.js # Export for Greenhouse ATS
node compiler/adapters/workday.js    # Export for Workday ATS
npx vitest run                       # Run all 29 tests
cd mcp-server; npx tsx src/index.ts  # Start MCP server (stdio)
cd mcp-server; npx tsx src/index.ts --http  # Start MCP (HTTP :3001)
```
