# TalentScout — Project Context

> This file is the living context document for the TalentScout project.
> Future agent sessions should read this file first to understand the project's goals, decisions, and current state.

---

## What Is TalentScout?

TalentScout is a **resume-as-code portfolio system** that:
1. Stores professional identity data in a single `data/resume.json` (JSON Resume standard, extended with `tags`)
2. Compiles it into Markdown, HTML, and PDF via a build pipeline
3. Serves a **premium interactive landing page** with a real-time Focus Selector (Frontend / Backend / Leadership / Open Source)
4. Exposes resume data via a **Model Context Protocol (MCP) server** for AI agent interoperability
5. Exports ATS-formatted profiles for **Greenhouse** and **Workday** via adapter scripts

---

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Data format | JSON Resume standard (extended) | Machine-readable, schema-validatable, widely supported |
| Schema enforcement | AJV + JSON Schema (draft-07) | Strict validation with format checking (email, URI) |
| Compiler | Plain Node.js ESM scripts | Zero framework overhead, simple dependency chain |
| MCP transport | stdio (default) + HTTP (--http flag) | stdio for local agent tools; HTTP for web-based clients |
| Landing page | Vanilla HTML/CSS/JS | No framework dependency; fast, embeddable anywhere |
| Tests | Vitest | Fast, ESM-native, minimal config |
| PDF generation | Puppeteer (headless Chrome) | No LaTeX; requires Chrome only |

---

## Project Status (as of 2026-07-11)

- ✅ **M1**: Scaffold complete — `package.json`, `resume.json`, `schema.json`, MCP `tsconfig.json`
- ✅ **M2**: Compiler pipeline — `validate.js`, `build.js` (MD + HTML), `--pdf` flag
- ✅ **M3**: Test suite — **29/29 tests passing** (schema matrix + compiler integrity)
- ✅ **M4**: MCP Server — 7 tools, stdio + HTTP transports, TypeScript strict
- ✅ **M5**: ATS Adapters — Greenhouse + Workday
- ✅ **M6**: Premium Landing Page — dark glassmorphism design, Focus Selector, MCP button, toast system

---

## What Needs To Be Done Next

- [ ] Replace placeholder `Alex Rivera` data in `data/resume.json` with real user data
- [ ] Deploy `web/` to GitHub Pages, Vercel, or Netlify for public access
- [ ] Register the MCP server in Claude Desktop or Cursor (`claude_desktop_config.json`)
- [ ] Implement SpacetimeDB integration for build history and test run logs (from project vision)
- [ ] Add DOCX export (pandoc-based, per original resume-as-code spec)
- [ ] Add a `--watch` mode to the compiler for live-reload during editing

---

## Key Files

| File | Purpose |
|---|---|
| [data/resume.json](data/resume.json) | **Edit this** — your professional identity |
| [schema/resume.schema.json](schema/resume.schema.json) | AJV JSON Schema for validation |
| [compiler/validate.js](compiler/validate.js) | Run to validate resume.json |
| [compiler/build.js](compiler/build.js) | Run to compile to MD + HTML + PDF |
| [compiler/adapters/greenhouse.js](compiler/adapters/greenhouse.js) | Greenhouse ATS export |
| [compiler/adapters/workday.js](compiler/adapters/workday.js) | Workday ATS export |
| [mcp-server/src/index.ts](mcp-server/src/index.ts) | MCP server — 7 agent tools |
| [web/index.html](web/index.html) | Landing page entry point |
| [web/app.js](web/app.js) | Dynamic resume renderer + Focus Selector |
| [web/style.css](web/style.css) | Dark-mode design system |
| [tests/schema.test.js](tests/schema.test.js) | 17 schema tests incl. error matrix |
| [tests/compiler.test.js](tests/compiler.test.js) | 12 compiler integrity tests |
| [docs/project_vision.md](docs/project_vision.md) | Master Vision (from interviewer session) |
| [docs/implementation_plan.md](docs/implementation_plan.md) | Architect's granular task breakdown |
| [docs/conversation_history.md](docs/conversation_history.md) | Origin conversation summary |

---

## MCP Tools Reference

| Tool | Params | Returns |
|---|---|---|
| `get_basics` | — | name, email, phone, location, profiles |
| `get_experience` | `company?` (string) | filtered work history |
| `get_skills` | `keyword?` (string) | filtered skills + keywords |
| `get_education` | — | all education entries |
| `get_projects` | `tag?` (string) | filtered projects by tag |
| `search_capabilities` | `query` (string) | full-text search results |
| `generate_ats_profile` | `format?` (greenhouse\|workday\|generic) | flat ATS object |

---

## Quick Commands

```powershell
# From talentscout/
node compiler/validate.js              # Validate data
node compiler/build.js                 # Build MD + HTML
node compiler/build.js --pdf           # Build + PDF
npx vitest run                         # Run all 29 tests
cd mcp-server; npx tsx src/index.ts    # Start MCP (stdio)
cd mcp-server; npx tsx src/index.ts --http  # Start MCP (HTTP :3001)
```
