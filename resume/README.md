# TalentScout — Resume as Code

A dynamic portfolio landing page powered by a JSON/YAML resume engine, an MCP server, and ATS export adapters.

## Project Structure

```
talentscout/
├── data/
│   └── resume.json          # Single source of truth (JSON Resume standard)
├── schema/
│   └── resume.schema.json   # JSON Schema for validation
├── compiler/
│   ├── build.js             # Main compiler: JSON → Markdown / HTML / PDF
│   ├── validate.js          # Schema validation runner
│   └── adapters/
│       ├── greenhouse.js    # ATS adapter: Greenhouse format
│       └── workday.js       # ATS adapter: Workday format
├── mcp-server/
│   ├── src/
│   │   └── index.ts         # MCP Server (TypeScript, @modelcontextprotocol/sdk)
│   ├── package.json
│   └── tsconfig.json
├── web/
│   ├── index.html           # Landing page
│   ├── style.css            # Premium styles
│   └── app.js               # Focus Selector + interactive resume
├── tests/
│   ├── schema.test.js       # JSON Schema validation tests
│   ├── compiler.test.js     # Compiler output integrity tests
│   └── error-matrix.test.js # Bad JSON permutation error injection tests
└── package.json
```

## Quick Start

```bash
npm install
node compiler/validate.js        # Validate resume.json
node compiler/build.js           # Compile to HTML + Markdown + PDF
node compiler/adapters/greenhouse.js  # Export for Greenhouse ATS
npm test                         # Run all tests
npm run mcp                      # Start MCP server
```
