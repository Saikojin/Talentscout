# Master Vision: TalentScout Resume Integration

This project integrates a "resume-as-code" engine into the TalentScout project to build a highly customizable, modern portfolio landing page, alongside a Model Context Protocol (MCP) server and automation scripts that format and export resume variants for ATS systems (like Greenhouse or Workday).

## The Story (Phase 1)
- **The "Why"**: Traditional resumes are static documents. By managing resume data in a single, robust JSON/YAML source of truth, we can build a dynamic portfolio landing page that lets users filter capabilities, toggle variants in real-time, and download tailored PDFs/DOCXs.
- **Primary Audience**: Prospective employers, ATS systems (Greenhouse/Workday), and AI agents using Model Context Protocol (MCP).
- **Core Value Proposition**:
  - **Single Source of Truth**: YAML/JSON resume data compiled into Markdown, HTML, and PDF.
  - **Dynamic Portfolio**: A landing page allowing real-time variant filtering and exports.
  - **AI Agent Native**: An MCP server that allows external AI agents to query the candidate's skills, experience, and projects directly with zero manual entry.
  - **ATS Adaptors**: Command-line scripts that format resume data specifically to match common ATS schemas (Greenhouse, Workday, etc.).

## Technical Architecture & Personas (Phase 2)

### CTO & QA Alignment: The Stack & Testing
- **Data Engine**: A YAML/JSON schema (extending JSON Resume standard).
- **Compiler**: A build pipeline that parses the YAML/JSON and generates Markdown, PDF (via Chrome headless), and HTML templates.
- **MCP Server**: An integration-ready MCP server exposing tools like `get_experience`, `search_skills`, and `generate_ats_profile`.
- **Validation Pipeline**:
  - Strict JSON Schema validation built into the compiler pipeline.
  - Automated tests validating structural integrity.
  - Error-injection matrix tests running a suite of common bad JSON/YAML permutations to ensure clean failure modes and error reporting.
  - **SpacetimeDB Integration**: Store test memories, build history, and run logs in SpacetimeDB to track historical schema performance.

### Design Alignment: The Landing Page Experience
- **Focus Selector**: An interactive slider/button group (e.g. "Frontend", "Backend", "Leadership") that dynamically filters, reorders, and highlights matching items with smooth micro-animations.
- **AI Integrations**: A prominent "Plug into MCP" action next to traditional PDF and DOCX download buttons, copy-pasting the local/hosted MCP connection URL for AI agents to query.

---

## Decision Log

| # | Decision | Rationale |
|---|---|---|
| 1 | JSON/YAML as source of truth (not raw Markdown partials) | Machine-readable, schema-validatable, drives both UI and API |
| 2 | MCP server as primary AI integration layer | Zero-manual-entry import for any MCP-compatible agent |
| 3 | ATS export scripts for Greenhouse & Workday | Most common enterprise hiring systems |
| 4 | Focus Selector with micro-animations on landing page | Dynamic, premium UX that highlights relevant skills per audience |
| 5 | Error-injection test matrix (16 permutations) | Ensures compiler fails gracefully on real-world data corruption |
| 6 | SpacetimeDB for build/test history (planned) | Persistent memory for agent sessions and CI tracking |
