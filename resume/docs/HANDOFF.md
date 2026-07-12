# TalentScout — Session Handoff

> **Conversation ID**: `d255684e-3bb3-4985-b0f5-4ffbdf9d03fc`
> **Session dates**: 2026-07-10 → 2026-07-11
> **Handed off**: 2026-07-11T20:47Z
> **Workspace**: `D:\DevWorkspace\TalentScout`

---

## 1. Context Snapshot

This conversation spanned ideation, architecture, full implementation, and a workspace correction for the TalentScout project. The incoming agent should read `CONTEXT.md` at the project root first, then this document.

**TalentScout** is two things in one project:

| Component | Description | Status |
|---|---|---|
| Python job scraper | Playwright-based multi-site job tracker with SQLite dedup and a FastAPI dashboard | ✅ Pre-existing, untouched |
| Resume-as-code engine | Node.js compiler + MCP server + interactive portfolio landing page | ✅ Fully built this session |

---

## 2. What Was Built This Session

### Phase 1 — Vision (seikoclaw-interviewer)
Four-persona interview established all core decisions:
- **JSON/YAML as single source of truth** (not static document fragments)
- **Compiler pipeline**: JSON → Markdown → HTML → PDF (puppeteer)
- **MCP server** with 7 tools for AI agent interoperability
- **Focus Selector** landing page with micro-animations (`highlightPulse`, `fadeSlideIn`)
- **ATS adapters** for Greenhouse and Workday
- **Error-injection test matrix** (16 bad-data permutations)

### Phase 2 — Architecture (seikoclaw-architect)
Six milestones, each with ≤5 files per task. All milestones executed and verified.

### Phase 3 — Implementation + Verification
All files built and verified in `D:\DevWorkspace\TalentScout\resume\`:

```
resume/
├── data/resume.json                  ← Source of truth (placeholder: Alex Rivera)
├── schema/resume.schema.json         ← AJV strict schema
├── compiler/
│   ├── validate.js                   ← Schema validator with error table
│   ├── build.js                      ← JSON → MD + HTML + PDF (--pdf flag)
│   └── adapters/
│       ├── greenhouse.js             ← Greenhouse Harvest API format
│       └── workday.js                ← Workday integration profile format
├── mcp-server/
│   └── src/index.ts                  ← 7-tool MCP server (stdio + HTTP)
├── web/
│   ├── index.html                    ← Portfolio landing page (SEO, OG, a11y)
│   ├── style.css                     ← Dark glassmorphism design system
│   └── app.js                        ← Dynamic renderer + Focus Selector
├── tests/
│   ├── schema.test.js                ← 17 tests: happy path + 16 error matrix
│   └── compiler.test.js              ← 12 tests: output integrity
└── docs/
    ├── project_vision.md
    ├── implementation_plan.md
    └── conversation_history.md
```

### Phase 4 — Workspace Correction
The project was initially built in the wrong location (`C:\Users\saiko\.gemini\antigravity\scratch\talentscout`). All files were migrated via `robocopy` to the correct workspace at `D:\DevWorkspace\TalentScout\resume\` and dependencies reinstalled. **All 29 tests pass in the correct location.**

---

## 3. Verified Outputs

| Command | Result |
|---|---|
| `node compiler/validate.js` | ✅ Valid — Alex Rivera |
| `node compiler/build.js` | ✅ `dist/resume.md` + `dist/resume.html` |
| `node compiler/adapters/greenhouse.js` | ✅ `dist/greenhouse_application.json` |
| `node compiler/adapters/workday.js` | ✅ `dist/workday_profile.json` |
| `npx vitest run` | ✅ **29/29 tests pass** |
| `npx tsc --noEmit` (mcp-server) | ✅ No TypeScript errors |
| MCP server (stdio) | ✅ Booted: "Alex Rivera" |

---

## 4. MCP Server — Tool Reference

Server starts on `stdio` (default) or `http://localhost:3001/mcp` (`--http` flag).

| Tool | Input Params | Returns |
|---|---|---|
| `get_basics` | — | name, email, phone, location, profiles |
| `get_experience` | `company?` (string) | filtered work history |
| `get_skills` | `keyword?` (string) | filtered skills + keywords |
| `get_education` | — | all education entries |
| `get_projects` | `tag?` (string) | projects filtered by tag |
| `search_capabilities` | `query` (string) | full-text match across skills/work/projects |
| `generate_ats_profile` | `format?` (greenhouse\|workday\|generic) | flat ATS-ready object |

---

## 5. Open Items — Prioritized Backlog

| Priority | Item | Details |
|---|---|---|
| 🔴 **P0** | Replace placeholder resume data | Edit `resume/data/resume.json` — currently "Alex Rivera". Run `node compiler/validate.js` after. |
| 🟠 **P1** | Register MCP server in agent config | Add `http://localhost:3001/mcp` to Claude Desktop `claude_desktop_config.json` or Cursor MCP settings |
| 🟠 **P1** | Deploy landing page | Deploy `resume/web/` to GitHub Pages, Vercel, or Netlify for public access |
| 🟡 **P2** | SpacetimeDB integration | QA vision item: persist build run logs, test history, schema performance into SpacetimeDB. Needs schema design before implementation. |
| 🟡 **P2** | DOCX export | Mentioned in vision (pandoc-based). Not designed yet. |
| 🟢 **P3** | `--watch` mode | Live-reload compiler while editing `resume.json`. Simple `chokidar` watcher around `build.js`. |

---

## 6. Architectural Decisions — Do Not Revisit Without Good Reason

| Decision | Choice | Why |
|---|---|---|
| Source of truth format | JSON (JSON Resume standard + `tags` extension) | Machine-readable, schema-validatable, drives UI and API simultaneously |
| Schema enforcement | AJV strict mode + `ajv-formats` | Catches type errors, bad email/URI formats, unknown properties |
| Compiler runtime | Node.js ESM (no framework) | Zero overhead, no build step, simple dependency chain |
| PDF generation | Puppeteer (headless Chrome) | No LaTeX; Chrome already on system for scraping |
| MCP transport | stdio default, `--http` flag optional | stdio for local tools; HTTP for browser/web clients |
| Landing page | Vanilla HTML/CSS/JS | No framework dependency — fast, portable, embeddable anywhere |
| Test runner | Vitest | Fast, ESM-native, no config needed |

---

## 7. Incoming Agent Instructions

> **First action**: Set workspace to `D:\DevWorkspace\TalentScout` and read `CONTEXT.md`.

**If continuing resume data work:**
1. Open `resume/data/resume.json`, replace placeholder data with real user info
2. Run `node compiler/validate.js` to confirm schema compliance
3. Run `node compiler/build.js` to regenerate dist artifacts

**If continuing MCP/server work:**
1. Source: `resume/mcp-server/src/index.ts`
2. Run with: `cd resume/mcp-server; npx tsx src/index.ts --http`
3. TypeScript must stay strictly clean: `npx tsc --noEmit` = 0 errors

**If adding SpacetimeDB:**
1. Read `resume/docs/project_vision.md` for QA requirements first
2. Design the schema (tables: `build_runs`, `test_results`, `schema_errors`) before coding
3. Use `seikoclaw-architect` to break into tasks before executing

**Before any code changes, always verify the baseline:**
```powershell
cd D:\DevWorkspace\TalentScout\resume
npx vitest run   # Must stay 29/29
```

---

## 8. Skills Used This Session

| Skill | Purpose | Outcome |
|---|---|---|
| `seikoclaw-harness` | Routing — which skill to start with | → `seikoclaw-interviewer` |
| `seikoclaw-interviewer` | Panel-based vision interview | → `resume/docs/project_vision.md` |
| `seikoclaw-architect` | Granular task decomposition | → 6 milestones, `implementation_plan.md` |
| `/goal` | Autonomous execution of all milestones | → All 6 milestones complete, 29/29 tests |
| `handoff` | This document | → `resume/docs/HANDOFF.md` |
