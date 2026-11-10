#!/usr/bin/env node
/**
 * resume/compiler/buildRolePackages.js
 *
 * Builds the 4 comprehensive Role Engineering Packages for Thomas S. Snyder (Saikojin):
 *   1. 01_Principal_QA_Architect_Enterprise_Cloud
 *   2. 02_Staff_Agentic_Harness_AI_Eval_Engineer
 *   3. 03_Principal_Technical_QA_Game_Tools_Lead
 *   4. 04_Principal_DevEx_Automation_Architect
 *
 * For EACH role, generates:
 *   - Career_Story.md, Career_Story.html, Career_Story.docx (Role-tailored Career Odyssey + D:\DevWorkspace chapters)
 *   - Cover_Letter.md, Cover_Letter.docx (With visually highlighted [[...]] manual keyword insertion slots)
 *   - Role-tailored Resumes (.docx and .md) in all 6 known ATS styles:
 *       * Resume_Standard (.docx / .md)
 *       * Resume_ATS_CAR (.docx / .md)   — Challenge -> Action -> Result
 *       * Resume_ATS_STAR (.docx / .md)  — Situation -> Task -> Action -> Result
 *       * Resume_ATS_LPS (.docx / .md)   — Leadership -> Problem-Solving -> Strategy/Success
 *       * Resume_ATS_ELITE (.docx / .md) — Elevate -> Leverage -> Illustrate -> Transfer -> Execute
 *       * Resume_ATS_WHO (.docx / .md)   — What -> How -> Outcome
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  AlignmentType,
  BorderStyle,
  ShadingType,
  Table,
  TableRow,
  TableCell,
  WidthType,
  HighlightColor
} from 'docx';

import { formatWorkEntryAts } from './atsFormatter.js';
import { generateStoryHtml } from './storyEngine.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const RESUME_ROOT = resolve(__dirname, '..');
const PROJECT_ROOT = resolve(RESUME_ROOT, '..');
const OUT_BASE = resolve(PROJECT_ROOT, 'tailored_outputs', 'Role_Packages');

const baseResume = JSON.parse(
  readFileSync(resolve(RESUME_ROOT, 'data', 'resume.json'), 'utf8')
);

// ─────────────────────────────────────────────────────────────────────────────
// HELPER: Parse text with [[PLACEHOLDER]] tokens into highlighted DOCX TextRuns
// ─────────────────────────────────────────────────────────────────────────────
function parseHighlightedRuns(text, baseOpts = {}) {
  const font = baseOpts.font || 'Arial';
  const size = baseOpts.size || 20;
  const color = baseOpts.color || '1a1a2e';
  const bold = baseOpts.bold || false;
  const italics = baseOpts.italics || false;

  const parts = String(text).split(/(\[\[[^\]]+\]\])/g);
  const runs = [];

  for (const part of parts) {
    if (!part) continue;
    if (part.startsWith('[[') && part.endsWith(']]')) {
      runs.push(
        new TextRun({
          text: part,
          bold: true,
          font,
          size,
          color: '991b1b', // Deep red text
          highlight: HighlightColor.YELLOW,
        })
      );
    } else {
      runs.push(
        new TextRun({
          text: part,
          bold,
          italics,
          font,
          size,
          color,
        })
      );
    }
  }
  return runs;
}

// ─────────────────────────────────────────────────────────────────────────────
// ROLE DEFINITIONS (4 MAPPED ARCHETYPES)
// ─────────────────────────────────────────────────────────────────────────────

const ROLE_PACKAGES = [
  // ===========================================================================
  // ROLE 1: ENTERPRISE CLOUD / SAAS — PRINCIPAL QA ARCHITECT
  // ===========================================================================
  {
    id: '01_Principal_QA_Architect_Enterprise_Cloud',
    roleTitle: 'Principal QA Architect / Staff Quality Systems Engineer',
    targetSector: 'Enterprise Cloud, Distributed SaaS & Platform Engineering',
    targetExamples: 'Microsoft, Smartsheet, Atlassian, AWS, Datadog, Salesforce, ServiceNow',
    summaryTemplate:
      'Principal-level Software Quality Architect and Senior SDET with 26+ years of experience driving zero-to-one test automation, cross-quadrant observability, and fault-tolerant release governance across Microsoft (5 tenures), Smartsheet, OpenMarket, and NVIDIA. Targeted for the [[TARGET_ROLE_TITLE]] role at [[COMPANY_NAME]], bringing deep mastery in [[JD_PRIMARY_KEYWORD_1]], [[JD_PRIMARY_KEYWORD_2]], and [[JD_PRIMARY_KEYWORD_3]]. Proven track record of building 1,500+ automated Karate/Playwright test suites from a zero baseline to replace 85% of manual regression, standardizing cloud microservice testing across AWS/Docker/Kubernetes, and correlating bare-metal/kernel telemetry to SaaS customer reliability.',
    keywordSlotLine:
      '[[JD_PRIMARY_KEYWORD_1]] · [[JD_PRIMARY_KEYWORD_2]] · [[JD_PRIMARY_KEYWORD_3]] · [[JD_CLOUD_OR_CI_TOOL]] · [[JD_DOMAIN_FOCUS]]',
    prioritizedSkills: [
      {
        name: 'Target Role & Company Alignment (Manual Keyword Zone)',
        level: 'Target Match',
        keywords: [
          '[[JD_PRIMARY_KEYWORD_1]]',
          '[[JD_PRIMARY_KEYWORD_2]]',
          '[[JD_PRIMARY_KEYWORD_3]]',
          '[[JD_CLOUD_OR_CI_TOOL]]',
          '[[JD_COMPLIANCE_OR_SLO_TERM]]',
        ],
      },
      {
        name: 'Enterprise Test Architecture & Automation',
        level: 'Expert',
        keywords: [
          'Karate DSL (0 to 1,500+ Tests / 85% Coverage)',
          'Playwright (Headless & Windowed E2E)',
          'Vitest / JUnit 5',
          'Visual UI Regression & Performance Gating',
          'Fit / FitNesse',
          'BrowserStack Cross-Browser & Mobile Farms',
        ],
      },
      {
        name: 'Distributed Systems, APIs & Chaos Engineering',
        level: 'Expert',
        keywords: [
          'REST & SOAP API Contract Testing',
          '5-Vector CI/CD Chaos Injection Matrices',
          'Microservice Bulkhead & Circuit Breaker Validation',
          'Man-in-the-Middle (MitM) Proxy Fault Injection',
          'Data Migration & ETL Pipeline Verification',
        ],
      },
      {
        name: 'Cross-Quadrant Telemetry & Kernel Forensics',
        level: 'Advanced',
        keywords: [
          'WinDbg Symbol-Connected Stack Trace Analysis',
          'Grafana / Graphite / Splunk Observability',
          'Windows ETW & BSOD BugCheck Correlation',
          'Hardware Lab Kit (HLK) & Windows Test Technologies (WTT)',
          'PXE / WMI Automated Bare-Metal Provisioning',
        ],
      },
      {
        name: 'Cloud Infrastructure & AI-Augmented Quality Gates',
        level: 'Advanced',
        keywords: [
          'AWS Cloud Microservices',
          'Docker & Kubernetes / Helm',
          'Jenkins / TeamCity / GitHub Actions CI/CD',
          'Model Context Protocol (MCP) QA Harnesses',
          'Anti-Soft-Pass Deterministic Verification Gates',
        ],
      },
    ],
    featuredProjects: [
      {
        name: 'Cross-Quadrant Telemetry & Chaos Injection Architecture (Enterprise Cloud Dossier)',
        url: 'https://github.com/Mr-Thomas-Snyder',
        description:
          'Executive quality architecture framework correlating 4 operational telemetry quadrants (Q1 Silicon/BMC -> Q2 OS Kernel/WinDbg -> Q3 Distributed Service Mesh -> Q4 SaaS RUM/Playwright) alongside a 5-Vector CI/CD Chaos Injection Matrix.',
        highlights: [
          'Designed lead-indicator correlation heuristics detecting hardware/kernel degradation 30–120 seconds before SaaS p99 SLO breach',
          'Specified automated CI/CD fault injection across malformed payloads, MitM network jitter, upstream dependency blackholing, pod resource starvation, and JWT security entropy',
          'Formalized the 30-60-90 Day "Rabbit" Rapid Assimilation Framework for turning legacy manual test debt into 85% automated CI/CD coverage',
        ],
        keywords: ['Karate DSL', 'Playwright', 'OpenTelemetry', 'WinDbg', 'Chaos Engineering', 'AWS/Azure'],
      },
      {
        name: 'qa-base & Enterprise Karate Modernization Suite',
        url: 'https://github.com/Mr-Thomas-Snyder',
        description:
          'Next-generation cross-platform Karate 1.4+ automation architecture built to modernize legacy enterprise web and API test suites across Windows, macOS, and Linux.',
        highlights: [
          'Eliminated brittle Selenium WebDriver dependencies in favor of native Chrome DevTools Protocol (CDP) and zero-friction driver resolution',
          'Integrated printed response payload receipts and post-action visual screenshot proofs into every HTML test report',
          'Containerized parallel execution pipelines for Docker and Jenkins CI/CD gates',
        ],
        keywords: ['Java 17', 'Karate 1.4', 'JUnit 5', 'Docker', 'Jenkins', 'Chrome CDP'],
      },
      {
        name: 'SeikoClaw-Harness & Seikojin QA Agent Cabinet',
        url: 'https://github.com/Saikojin/seikoclaw-harness',
        description:
          'Production-grade agentic quality harness encoding 26 years of SDET governance into deterministic `[GATE: QA]` and `[GATE: VISUAL_CRITIC]` verification contracts.',
        highlights: [
          'Enforces QA Constitution Rule #8 (Anti-Soft-Pass) prohibiting mock-only checks or static login-screen screenshots from passing CI',
          'Validated via empirical A/B benchmarking (ClawExerMart vs. RawExerMart), proving 100% defect containment across 12 engineering dimensions',
        ],
        keywords: ['Python', 'TypeScript', 'MCP', 'Playwright', 'Vitest', 'SQLite'],
      },
      {
        name: 'WinCrashInspector — Kernel & Hypervisor Forensics Toolkit',
        url: 'https://github.com/Mr-Thomas-Snyder',
        description:
          'PowerShell systems diagnostic suite automating Windows BSOD BugCheck correlation, HVCI/VBS virtualization audits, and Hyper-V micro-VM container tracing.',
        highlights: [
          'Automates correlation of kernel BugCheck codes (0x3B, 0x1E, 0x133, 0x139, 0x7E) against driver verifier states and kernel hooks',
          'Inspects active WSL2, Docker, and Windows Sandbox hypervisor partitions to isolate host-vs-container stability regressions',
        ],
        keywords: ['PowerShell', 'WinDbg', 'Windows Kernel', 'Hyper-V', 'Diagnostics'],
      },
    ],
    storyConfig: {
      subtitle: 'The Enterprise Cloud & Systems Quality Odyssey',
      tagline:
        'From bare-metal kernel debuggers and Fortune 500 migrations to 1,500-test cloud automation suites: 26+ years of turning quality engineering into organizational velocity.',
      synopsis: [
        'In enterprise software, the most expensive outages rarely announce themselves cleanly inside a single log file. They begin as subtle friction across siloed layers—a thermal throttle or driver fault in hardware, a silent schema drift in a Fortune 500 data migration, or a 40-hour manual regression bottleneck that paralyzes weekly SaaS releases. Across 26+ years spanning five tenures at Microsoft, NVIDIA, HP, OpenMarket, Apptio, and Smartsheet, Thomas S. Snyder has operated as the principal diagnostic bridge across every layer of that stack.',
        'Rather than treating Quality Assurance as a passive post-development gate, Snyder repeatedly stepped into organizations with zero automation baseline or entrenched cultural resistance and built the technical levers that transformed how they shipped. At Smartsheet, he architected a Karate DSL automation framework from scratch that grew to over 1,500 automated tests and replaced 85% of manual regression. At OpenMarket, he standardized reusable API test templates that accelerated company-wide migration of high-throughput SMS/MMS/RCS telecom services to AWS.',
        'Anchored by early mastery in bare-metal lab automation (PXE/WMI/WTT) and white-box WinDbg kernel crash forensics at Microsoft, and culminating in modern AI-governed quality harnesses (SeikoClaw-Harness), this odyssey demonstrates how ruthless triage, cross-quadrant observability, and zero-soft-pass automation allow enterprise engineering teams to ship with speed and mathematical confidence.',
      ],
      motto:
        'True enterprise resilience happens when silicon telemetry, API contracts, and user-facing journeys are verified as one continuous system—turning QA from a release bottleneck into the engine of deployment velocity.',
      stats: [
        { label: 'Enterprise Span', value: '26+ Years (18 Eras)' },
        { label: 'Smartsheet Impact', value: '0 → 1,500+ Automated Tests' },
        { label: 'Manual Regression Cut', value: '85% Replaced by Karate' },
        { label: 'Microsoft Tenures', value: '5 Core OS/Device/Media Roles' },
        { label: 'Stack Depth', value: 'Silicon · Kernel · Cloud API · UI' },
        { label: 'Target Focus', value: '[[COMPANY_NAME]] · [[TARGET_ROLE_TITLE]]' },
      ],
      workspaceChapters: [
        {
          company: 'Enterprise Cloud Quality Architecture (D:\\DevWorkspace)',
          position: 'Principal Quality Systems Architect — Cross-Quadrant Telemetry & Chaos Matrices',
          location: 'Redmond, WA',
          dateSpan: 'Jan 2026 – Present',
          duration: 'Current Frontier',
          tags: ['cloud', 'architecture', 'chaos-engineering', 'telemetry', 'karate', 'playwright'],
          paragraphs: [
            'Synthesizing 26 years of field-tested patterns across Microsoft hardware labs and Smartsheet/OpenMarket SaaS platforms, Thomas architected the Cross-Quadrant Telemetry Blueprint and 5-Vector CI/CD Chaos Injection Matrix within D:\\DevWorkspace.',
            'The core engineering challenge addressed the "Siloed Observability Fallacy": infrastructure teams track hypervisors, backend teams track gRPC status codes, and product teams track synthetic UI journeys in isolation—allowing kernel socket exhaustion or malformed upstream payloads to manifest as mysterious customer-facing outages. To solve this, Thomas designed a unified correlation plane linking Q1 Silicon (BMC/HLK), Q2 Kernel (ETW/WinDbg), Q3 Microservices (OpenTelemetry/Karate), and Q4 SaaS Experience (Playwright RUM), paired with automated chaos gates that inject malformed payloads, MitM latency jitter, and dependency blackholes directly in CI/CD.',
            'This architecture proved that hardware and kernel lead indicators precede SaaS SLO breaches by 30 to 120 seconds, enabling automated canary draining and circuit-breaker deflection before customers ever see a 5xx error.',
            'Complemented by WinCrashInspector (automated PowerShell BSOD BugCheck and Hyper-V container forensics) and qa-base (modernized cross-platform Karate 1.4+ CDP execution), these systems represent ready-to-deploy blueprints for [[COMPANY_NAME]].',
          ],
          lesson:
            'Correlating low-level kernel and network lead indicators with high-level API/UI contract tests transforms quality engineering from post-mortem triage into preemptive failure deflection.',
        },
      ],
    },
    coverLetterConfig: {
      subjectLine: 'Application for [[TARGET_ROLE_TITLE]] — [[COMPANY_NAME]]',
      openingHook:
        'I am writing to express my strong interest in the **[[TARGET_ROLE_TITLE]]** role at **[[COMPANY_NAME]]**. Over a 26-year career spanning five tenures at Microsoft, enterprise SaaS leadership at Smartsheet, and high-throughput AWS cloud migrations at OpenMarket, I have specialized in walking into complex, high-scale engineering environments and building the automated quality architectures that eliminate manual bottlenecks and prevent production escapes.',
      alignmentParagraph:
        'Your team’s focus on **[[COMPANY_PRODUCT_OR_PLATFORM]]** and requirement for deep expertise in **[[JD_PRIMARY_KEYWORD_1]]**, **[[JD_PRIMARY_KEYWORD_2]]**, and **[[JD_PRIMARY_KEYWORD_3]]** align directly with the systems I have delivered in production:\n\n' +
        '- **Zero-to-85% Enterprise Test Automation (Smartsheet):** Stepped into a manual-heavy web and application ecosystem with zero automation baseline. Architected a unified **Karate DSL** and **BrowserStack** framework from scratch that scaled to **1,500+ automated tests**, replacing **85% of manual regression** and expanding into visual UI comparison and performance gating.\n' +
        '- **Cloud Microservices & API Standardization (OpenMarket):** Drove quality standardization for mission-critical SMS, MMS, and RCS telecom microservices migrating to **AWS** with **Docker** and **Terraform**. Designed reusable Karate API contract templates that accelerated test onboarding across engineering squads.\n' +
        '- **Bare-Metal, Kernel & Cross-Quadrant Forensics (Microsoft & NVIDIA):** Engineered **WTT/HLK** and **PXE/WMI** automated test beds provisioning hundreds of devices overnight, while performing white-box **WinDbg** symbol-connected stack trace analysis to isolate kernel and driver boundary failures.',
      differentiatorParagraph:
        'Beyond traditional test automation, I bring an **AI-native Systems & DevEx mindset** specifically suited to solve **[[JD_SPECIFIC_CHALLENGE_OR_GOAL]]** for the **[[TEAM_OR_ORG_NAME]]** team. In my independent engineering workspace, I architected **SeikoClaw-Harness** (a 130+ skill agentic engineering and QA gatekeeping harness) and **TalentScout** (a resilient Playwright/FastAPI/MCP platform with automated rate-limiting circuit breakers and DOM selector drift self-healing). Whether designing a 5-Vector CI/CD Chaos Injection Matrix or executing my **30-60-90 Day "Rabbit" Rapid Assimilation Framework**, I focus on high-ROI automation that frees engineers to ship faster.',
      closingParagraph:
        'I would welcome the opportunity to discuss how my 26 years of enterprise quality architecture, Karate/Playwright automation mastery, and AI-assisted testing workflows can immediately strengthen **[[COMPANY_NAME]]**’s release velocity and reliability.',
    },
  },

  // ===========================================================================
  // ROLE 2: AI-FIRST / DEVTOOLS — STAFF AGENTIC HARNESS & AI EVAL ENGINEER
  // ===========================================================================
  {
    id: '02_Staff_Agentic_Harness_AI_Eval_Engineer',
    roleTitle: 'Staff Agentic Harness / AI Evaluation & Quality Engineer',
    targetSector: 'AI Research Labs, Agentic Coding Platforms & Next-Gen Developer Tools',
    targetExamples: 'Anthropic, OpenAI, Google DeepMind, Cursor, Vercel, Cloudflare, GitHub, Linear',
    summaryTemplate:
      'AI-Native Quality Systems Architect and Agentic Harness Engineer combining 26+ years of adversarial software testing (Microsoft, Smartsheet, OpenMarket, Xbox) with production design of multi-agent orchestration harnesses, Model Context Protocol (MCP) servers, local GGUF/SDXL inference engines, and deterministic AI evaluation gates. Targeted for the [[TARGET_ROLE_TITLE]] position at [[COMPANY_NAME]], bringing hands-on mastery in [[JD_PRIMARY_KEYWORD_1]], [[JD_PRIMARY_KEYWORD_2]], and [[JD_PRIMARY_KEYWORD_3]]. Creator of SeikoClaw-Harness (130+ modular skills, 24 core directives, 5-stage Goldfish spec reviews, and falsification gates) and OpenBrain (tiered SQLite/ChromaDB/SpacetimeDB semantic memory with Kompress token compression).',
    keywordSlotLine:
      '[[JD_PRIMARY_KEYWORD_1]] · [[JD_PRIMARY_KEYWORD_2]] · [[JD_PRIMARY_KEYWORD_3]] · [[JD_LLM_OR_AGENT_STACK]] · [[JD_EVAL_FRAMEWORK]]',
    prioritizedSkills: [
      {
        name: 'Target Role & Company Alignment (Manual Keyword Zone)',
        level: 'Target Match',
        keywords: [
          '[[JD_PRIMARY_KEYWORD_1]]',
          '[[JD_PRIMARY_KEYWORD_2]]',
          '[[JD_PRIMARY_KEYWORD_3]]',
          '[[JD_LLM_OR_AGENT_STACK]]',
          '[[JD_EVAL_OR_SAFETY_METRIC]]',
        ],
      },
      {
        name: 'Agentic Harness Architecture & MCP Orchestration',
        level: 'Expert',
        keywords: [
          'SeikoClaw-Harness (130+ Skills / 24 Core Directives)',
          'Model Context Protocol (MCP) Server Authoring (TypeScript & Python)',
          'DAG Task Decomposition & Worktree Concurrency',
          'Pre-Execution Shell Guardrails & Boundary Discipline',
          'Multi-Model Failover Orchestration (Claude / Gemini / Local GGUF)',
        ],
      },
      {
        name: 'AI Evaluation, Red-Teaming & Anti-Soft-Pass Gating',
        level: 'Expert',
        keywords: [
          '5-Stage Isolated "Goldfish" Spec Review Pipeline',
          'Adversarial Falsification Gates (gate:disproof)',
          'Skill Routing Evals & Vocabulary Collision Linting',
          'Empirical A/B Harness Benchmarking (ClawExerMart vs. RawExerMart)',
          'Anti-Soft-Pass Visual & Behavioral Verification Receipts',
        ],
      },
      {
        name: 'Semantic Memory, Context Compression & Local Inference',
        level: 'Advanced',
        keywords: [
          'OpenBrain Tiered Memory (SQLite + ChromaDB + SpacetimeDB WASM)',
          'Headroom Kompress & "Smart Caveman" DAG Token Compression',
          'Tiktoken Preflight Token Budgeting & Context Health Telemetry',
          'LocalMind Self-Healing GGUF Engine (llama.cpp / CUDA / psutil Auto-Tuning)',
          'ArtistAgent SDXL Local GPU Foundry (12GB VRAM Optimization)',
        ],
      },
      {
        name: 'Classical SDET & Deterministic Verification Foundations',
        level: 'Expert',
        keywords: [
          'Playwright (Stealth Anti-Bot & DOM Drift Self-Healing)',
          'Karate DSL (1,500+ API/UI/Visual Tests)',
          'Vitest / Pytest / JUnit 5',
          'Deterministic Algorithmic NLG (Zero-LLM-Tax Compilers)',
          '26+ Years Root-Cause Diagnostics (Microsoft, Smartsheet, Xbox)',
        ],
      },
    ],
    featuredProjects: [
      {
        name: 'SeikoClaw-Harness — Autonomous Agentic Engineering OS',
        url: 'https://github.com/Saikojin/seikoclaw-harness',
        description:
          'Production-grade agentic coding harness pairing 130+ specialized developer, QA, and game-dev skills with declarative playbooks, POSIX/PowerShell safety guardrails, and adversarial verification gates.',
        highlights: [
          'Engineered Tier 2 Skill Routing Evals (`eval-skills`) with automated YAML frontmatter linting, pairwise vocabulary collision detection, and canonical utterance benchmarks',
          'Implemented 5-stage isolated "Goldfish" specification reviews (`/spec-review`), multi-model red-teaming (`/interrogate`), and falsification gates (`gate:disproof`)',
          'Published the empirical ClawExerMart vs. RawExerMart A/B case study proving harness superiority across test coverage, security boundaries, and UI polish',
        ],
        keywords: ['Python', 'TypeScript', 'MCP', 'Headroom-AI', 'Tiktoken', 'Playwright', 'Vitest'],
      },
      {
        name: 'OpenBrain — Tiered Semantic Memory & Context Compression Sidecar',
        url: 'https://github.com/Mr-Thomas-Snyder',
        description:
          'Persistent cognitive memory sidecar for AI agents backed by SQLite, ChromaDB vector embeddings, and a C#/.NET 8.0 WASM SpacetimeDB 2.1 real-time synchronization module.',
        highlights: [
          'Designed 4-tier memory lifecycle (`Core`, `Longterm`, `Midterm`, `Shortterm`) with Fernet-encrypted secrets vault and provider token expenditure telemetry',
          'Built `ContextEngine` utilizing local LLMs and "Smart Caveman" DAG-fact compression to condense verbose session logs without losing architectural invariants',
        ],
        keywords: ['Python', 'SQLite', 'ChromaDB', 'C# / .NET 8 WASM', 'SpacetimeDB', 'Vector Embeddings'],
      },
      {
        name: 'LocalMind & LLMWorkbench — Self-Healing Local GGUF & MCP Platform',
        url: 'https://github.com/Mr-Thomas-Snyder',
        description:
          'Unified local/cloud LLM inference library (`localmind` v1.0.0) and FastAPI/React/MCP orchestration workbench running quantised GGUF models on local GPU/CPU.',
        highlights: [
          'Engineered hardware auto-tuning (`psutil` RAM/VRAM/CPU inspection) to dynamically size context windows and thread allocations',
          'Built self-healing inference loops that intercept native C++ `llama_decode returned -1` VRAM overflows and transparently re-initialize context',
          'Exposed MCP tools for zero-cost local prompt expansion, log summarization, and embedded game runtime intelligence',
        ],
        keywords: ['Python', 'FastAPI', 'React 18', 'llama-cpp-python', 'GGUF', 'CUDA', 'MCP'],
      },
      {
        name: 'TalentScout — Agentic Job Scouring & Deterministic Resume-as-Code MCP Engine',
        url: 'https://github.com/Saikojin/Talentscout',
        description:
          'Playwright stealth job discovery platform paired with a Node.js ESM/TypeScript Resume-as-Code compiler and 7-tool MCP server.',
        highlights: [
          'Built zero-dependency Playwright stealth evasion, HTTP 429 5-minute circuit breakers, and heuristic DOM selector drift self-healing',
          'Authored a 100% deterministic, LLM-free Natural Language Generation engine (`storyEngine.js`) transforming structured career JSON into multi-perspective narrative odysseys verified by 38/38 Vitest tests',
        ],
        keywords: ['TypeScript', 'Node.js ESM', 'MCP SDK', 'Playwright', 'FastAPI', 'SQLite', 'Vitest'],
      },
    ],
    storyConfig: {
      subtitle: 'The Agentic Harness & AI Evaluation Odyssey',
      tagline:
        'Why raw AI coding agents fail for the exact same reasons untested enterprise software fails—and how 26 years of adversarial QA built the harness to govern them.',
      synopsis: [
        'When large language models began writing production software, most of the industry treated them like magic chat boxes—and quickly drowned in hallucinated APIs, silent regressions, context window amnesia, and "soft-pass" tests that asserted dummy values. Thomas S. Snyder looked at those failure modes through a very different lens: 26+ years on the front lines of software quality engineering at Microsoft, NVIDIA, OpenMarket, Smartsheet, and Xbox.',
        'Having spent a quarter-century hunting down race conditions in Windows OS hardware labs, pioneering the exploit-driven "Rabbit" completion role on the original Xbox, and building 1,500-test Karate automation suites from scratch at Smartsheet, Snyder recognized that an un-harnessed AI agent is simply an undisciplined developer without a CI gate. In response, he architected SeikoClaw-Harness, OpenBrain, LocalMind, and the Seikojin QA Agent Cabinet inside D:\\DevWorkspace.',
        'This odyssey chronicles the evolution from classical bare-metal and cloud QA to frontier Agentic Harness Engineering: replacing fragile prompt-engineering wishful thinking with 24 first-principle rules, isolated 5-stage "Goldfish" spec reviews, falsification gates (`gate:disproof`), semantic memory compression, and non-headless visual receipt verification.',
      ],
      motto:
        'An AI agent without a deterministic verification harness is just a fast way to generate technical debt. Govern the context, falsify the assumptions, and demand runtime receipts.',
      stats: [
        { label: 'Agentic Harness', value: '130+ Skills · 24 Core Rules' },
        { label: 'Empirical Corpus', value: '348 Sessions · 1,227 Prompts' },
        { label: 'Memory Sidecar', value: 'SQLite · ChromaDB · SpacetimeDB' },
        { label: 'Verification Baseline', value: '0 → 1,500+ Karate/E2E Tests' },
        { label: 'Local AI Stack', value: 'Self-Healing GGUF & SDXL' },
        { label: 'Target Focus', value: '[[COMPANY_NAME]] · [[TARGET_ROLE_TITLE]]' },
      ],
      workspaceChapters: [
        {
          company: 'SeikoClaw-Harness & OpenBrain (D:\\DevWorkspace)',
          position: 'Creator & Principal Agentic Harness Architect',
          location: 'Redmond, WA',
          dateSpan: 'Jan 2024 – Present',
          duration: 'Current Frontier',
          tags: ['ai', 'mcp', 'agents', 'evals', 'memory', 'automation'],
          paragraphs: [
            'Confronting the reality of multi-session context drift, UI slop, and "soft-pass" agent self-grading across 348 real engineering sessions, Thomas architected SeikoClaw-Harness and its persistent cognitive sidecar, OpenBrain.',
            'To prevent agents from grading their own homework or blowing through 250k+ token budgets, he engineered a multi-layered control loop: (1) `/seikoclaw-architect` DAG decomposition with explicit human decision gates; (2) a 5-stage isolated "Goldfish" specification review pipeline where fresh-context critics tear apart assumptions before code is written; (3) OpenBrain tiered memory combining SQLite, ChromaDB vector search, SpacetimeDB WASM sync, and Headroom Kompress / "Smart Caveman" token compression; and (4) `seikojin-qa` anti-soft-pass gates requiring printed API payloads and live windowed screenshot receipts.',
            'To prove the harness worked empirically rather than anecdotally, he executed a controlled A/B experiment—building `RawExerMart` (unassisted prompt) and `ClawExerMart` (SeikoClaw-governed) from the exact same specification, demonstrating dramatic gains across 12 architectural and QA dimensions. When an external auditor critiqued early stub functions in SeikoClaw, Thomas immediately ingested the critique into `/architect` and systematically remediated every finding with automated routing evals (`eval-skills`).',
            'Paired with LocalMind and LLMWorkbench—which provide self-healing local GGUF inference that automatically recovers from native `llama_decode` VRAM crashes—this ecosystem represents a complete blueprint for reliable agentic engineering at [[COMPANY_NAME]].',
          ],
          lesson:
            'Reliable autonomous engineering requires separating the actor from the verifier: pair context-compressed planning with isolated adversarial critics and hard runtime falsification gates.',
        },
      ],
    },
    coverLetterConfig: {
      subjectLine: 'Application for [[TARGET_ROLE_TITLE]] — [[COMPANY_NAME]]',
      openingHook:
        'I am writing to apply for the **[[TARGET_ROLE_TITLE]]** position at **[[COMPANY_NAME]]**. Most engineers approaching agentic AI come solely from model training or web application backgrounds; I approach it from **26+ years of breaking, diagnosing, and automating complex software systems** across Microsoft, Smartsheet, OpenMarket, NVIDIA, and Xbox—and translating those exact quality disciplines into production **AI Agent Harnesses, MCP Tooling, and Deterministic Evaluation Pipelines**.',
      alignmentParagraph:
        'Your work on **[[COMPANY_PRODUCT_OR_PLATFORM]]** and focus on **[[JD_PRIMARY_KEYWORD_1]]**, **[[JD_PRIMARY_KEYWORD_2]]**, and **[[JD_PRIMARY_KEYWORD_3]]** address the exact problems I have been solving daily across 348+ engineering sessions in my own agentic ecosystem:\n\n' +
        '- **Production Agentic Harness & Routing Evals (`SeikoClaw-Harness`):** Architected a 130+ skill agentic harness enforcing 24 engineering directives, pre-execution shell guardrails, 5-stage isolated "Goldfish" spec reviews (`/spec-review`), falsification gates (`gate:disproof`), and automated skill-routing evaluation suites (`eval-skills`) with vocabulary collision linting.\n' +
        '- **Tiered Semantic Memory & Token Compression (`OpenBrain` & `LocalMind`):** Built a persistent cognitive sidecar combining **SQLite**, **ChromaDB** vector embeddings, and **.NET 8 WASM SpacetimeDB** with **Headroom Kompress** and `tiktoken` preflight budgeting—paired with a self-healing `llama.cpp` GGUF engine that auto-recovers from native C++ VRAM decode crashes.\n' +
        '- **Anti-Soft-Pass Verification & Empirical A/B Benchmarking:** Eliminated AI "soft passes" (such as agents passing broken 3D camera inversions or static login screenshots) by encoding **QA Constitution Rule #8** into `/seikojin-qa`, and proved harness efficacy through a 12-dimension controlled A/B study (`ClawExerMart` vs. `RawExerMart`).',
      differentiatorParagraph:
        'Combined with my enterprise track record—such as building a **1,500+ test Karate framework from zero at Smartsheet** to replace 85% of manual regression—I bring a battle-tested ability to tackle **[[JD_SPECIFIC_CHALLENGE_OR_GOAL]]** within the **[[TEAM_OR_ORG_NAME]]** team. I know where AI agents hallucinate, how tests lie when assertions are weak, and how to build the deterministic levers and MCP bridges that make autonomous workflows trustworthy.',
      closingParagraph:
        'I would love to share my live repositories (`SeikoClaw-Harness`, `OpenBrain`, `TalentScout` MCP) and discuss how I can help **[[COMPANY_NAME]]** push the frontier of reliable, verifiable AI systems.',
    },
  },

  // ===========================================================================
  // ROLE 3: GAME STUDIOS & SIMULATION TECH — PRINCIPAL TECHNICAL QA & TOOLS LEAD
  // ===========================================================================
  {
    id: '03_Principal_Technical_QA_Game_Tools_Lead',
    roleTitle: 'Principal Technical QA Architect / Game Tools & Automation Lead',
    targetSector: 'AAA/AA Game Studios, Game Engines, Simulation Tech & Virtual Tabletops',
    targetExamples: 'Xbox Game Studios, Valve, Epic Games, Unity, Bungie, Monolith, Wizards of the Coast',
    summaryTemplate:
      'Veteran Game & Simulation Quality Architect with 26+ years spanning the original Xbox TCR certification team (where I pioneered the dedicated "Rabbit" speedrun-completion testing role), Microsoft Game Studios, Monolith Productions, and Nintendo of America—now architecting AI-governed multi-engine game automation and 3D DCC pipelines across Unreal Engine 5.7/5.8 (C++20), Unity 6 (C#), Godot 4 (GDScript), and Blender 5.2 MCP. Targeted for the [[TARGET_ROLE_TITLE]] role at [[COMPANY_NAME]], bringing deep expertise in [[JD_PRIMARY_KEYWORD_1]], [[JD_PRIMARY_KEYWORD_2]], and [[JD_PRIMARY_KEYWORD_3]]. Proven track record of shipping 70+ headless Unreal C++ automation specs, 101+ Karate E2E gameplay scenarios, custom in-game diagnostic terminals, and standalone physics/audio balance workbenches.',
    keywordSlotLine:
      '[[JD_PRIMARY_KEYWORD_1]] · [[JD_PRIMARY_KEYWORD_2]] · [[JD_PRIMARY_KEYWORD_3]] · [[JD_GAME_ENGINE_OR_DCC]] · [[JD_GENRE_OR_SYSTEM]]',
    prioritizedSkills: [
      {
        name: 'Target Role & Company Alignment (Manual Keyword Zone)',
        level: 'Target Match',
        keywords: [
          '[[JD_PRIMARY_KEYWORD_1]]',
          '[[JD_PRIMARY_KEYWORD_2]]',
          '[[JD_PRIMARY_KEYWORD_3]]',
          '[[JD_GAME_ENGINE_OR_DCC]]',
          '[[JD_MULTIPLAYER_OR_CONSOLE_CERT]]',
        ],
      },
      {
        name: 'Multi-Engine Game Automation & Headless C++/C# Testing',
        level: 'Expert',
        keywords: [
          'Unreal Engine 5.5–5.8 C++20 Automation Specs (70+ Headless Tests)',
          'Unity 6 (6000.x LTS) EditMode & PlayMode Automated Assemblies',
          'Godot 4.3–4.5 GDScript & Headless Physics Validators',
          'Karate DSL Full-Stack Gameplay "Rabbit Path" E2E Suites (101+ Scenarios)',
          'Playwright WebGL / PixiJS / Canvas Visual & Telemetry Verification',
        ],
      },
      {
        name: 'In-Engine Diagnostic Tooling, MCP Bridges & Workbenches',
        level: 'Expert',
        keywords: [
          'Custom In-Game Tilde (`~`) Diagnostic Terminals & Coordinate Reticles',
          'UnrealMCP, Godot-MCP & Blender 5.2 MCP Live Editor Automation',
          'Zero-Install HTML5 Physics, Aerodynamic & Web Audio Workbenches',
          '68.4 MB SQLite Rules Vaults & Deterministic Combat Simulators',
          'WinDbg Crash Dump & GPU/Hardware Compatibility Matrices',
        ],
      },
      {
        name: 'Console Certification (TCR), Live-Ops & Exploit Hunting',
        level: 'Expert',
        keywords: [
          'Original Xbox "Rabbit" End-to-End Speedrun/Exploit Methodology Pioneer',
          'Xbox Technical Certification Requirements (TCR) — 4x Throughput Scaling',
          'Live MMORPG Game Master In-Engine Debugging (1,300+ Tickets/Week)',
          'Side-by-Side (SxS) Visual Bar Parity & Anti-Soft-Pass Shader Audits',
          'PC / Console Hardware Lab Provisioning (WMI / PXE / Ghost / DirectX)',
        ],
      },
      {
        name: 'Enterprise Automation & Cross-Discipline Leadership',
        level: 'Expert',
        keywords: [
          'Karate Framework (0 to 1,500+ Tests / 85% Manual Regression Cut at Smartsheet)',
          'Game Forge Autonomous Stage-Gate Pipeline (Stages A–E)',
          'Offshore & Studio-Wide QA Training, Playbooks & Triage Governance',
          'Python, C++20, C#, GDScript, JavaScript/TypeScript, SQLite',
        ],
      },
    ],
    featuredProjects: [
      {
        name: 'TacticalAdberrainUE & Tactical-Adberrain — Multi-Generational RPG & 171-Test Suite',
        url: 'https://github.com/Mr-Thomas-Snyder',
        description:
          'Spherical hex-globe tactical RPG migrated from a WebGL/Flask architecture (`Tactical-Adberrain` with 36 Jest suites, 320+ Pytest items, and 101 Karate E2E scenarios) to native Unreal Engine 5.8 C++ (`TacticalAdberrainUE`) with Blender 5.2 assets.',
        highlights: [
          'Engineered a 15-table SQLite Vault database (68.4 MB D&D 3.5e SRD: 2,605 spells, 1,277 feats, 984 monsters) and 5-book deterministic rules engine in UE 5.8 C++',
          'Built 70+ native headless Unreal C++ automation tests (`EXIT CODE: 0`) plus in-game `~` diagnostic terminals and `mark_start` targeting reticles to eliminate spherical hex-seam and LOD zoom drift',
          'Caught and fixed an inverted-globe sky-fog QA "soft pass" at 10-mile camera elevation by replacing naive pixel-color checks with strict geometric normal and horizon verification',
        ],
        keywords: ['Unreal Engine 5.8', 'C++20', 'Slate UI', 'Blender 5.2 MCP', 'SQLite', 'Karate DSL', 'Playwright'],
      },
      {
        name: '1914 WWI Pioneer Aerial Combat Tri-Engine Trilogy (WWPatrick, WWUnity, WWGodot)',
        url: 'https://github.com/Mr-Thomas-Snyder',
        description:
          'Cross-engine engineering benchmark implementing the exact same 1914 rotary-engine biplane physics simulation (gyroscopic precession torque, adverse yaw, canvas tear, cockpit gunplay) across Unreal 5.7 C++20, Unity 6 URP C#, and Godot 4.5 GDScript.',
        highlights: [
          'WWPatrick (UE 5.7 C++20): Custom Newtonian airframe solver (`AWWPAirframeComponent`), server-authoritative 1v1 replication, 7 C++ automation specs, and 11-step E2E Rabbit Path certification',
          'WWUnity (Unity 6 C#): EditMode/PlayMode test assemblies paired with standalone HTML5 aerodynamic and Web Audio rotary engine synthesizer workbenches (`aero_balance_simulator.html`)',
          'WWGodot (Godot 4.5): Blender MCP procedural aircraft pipeline (`early_biplane.glb`) validated by Python flight-envelope balance scripts (`validate_flight_balance.py`)',
        ],
        keywords: ['Unreal 5.7 C++20', 'Unity 6 C#', 'Godot 4.5 GDScript', 'Blender MCP', 'Physics Simulation', 'Game Forge'],
      },
      {
        name: 'Tablebuddy, BookIngestion & Perplexed — Local-First VTT & Embedded AI Games',
        url: 'https://github.com/Mr-Thomas-Snyder',
        description:
          'Hardware-accelerated React/PixiJS WebGL Virtual Tabletop (`Tablebuddy`), 8-stage RPG PDF rulebook compiler (`BookIngestion`), and standalone embedded-GGUF riddle game (`Perplexed`).',
        highlights: [
          'Resolved native C++ `llama.dll` / `ggml` Access Violations in PyInstaller standalone game builds and benchmarked sub-4s inference across quantized 1B/0.6B models',
          'Built Universal VTT (`.uvtt`/`.dd2vtt`) line-of-sight wall/portal importers, WebGL Fog-of-War shaders, and isolated Karate E2E contract suites',
        ],
        keywords: ['PixiJS / WebGL', 'FastAPI', 'PyWebView', 'llama.cpp', 'Godot 4.5', 'Karate E2E'],
      },
    ],
    storyConfig: {
      subtitle: 'The Game Systems, Console Certification & Multi-Engine Tooling Odyssey',
      tagline:
        'From N64 EPROM cartridges and pioneering the original Xbox "Rabbit" speedrun role to 70+ headless Unreal 5.8 C++ automation tests and tri-engine physics workbenches.',
      synopsis: [
        'Game development is the ultimate crucible for software quality: real-time 60 FPS frame budgets, non-deterministic physics, complex 3D asset pipelines, and thousands of interacting state rules where a single inverted normal or broken close button ruins player immersion. Thomas S. Snyder’s relationship with that crucible began in 1999 at Nintendo of America—burning N64 and Game Boy builds onto EPROM chips and recording speedrun exploits onto VHS tape—and accelerated on the original Xbox console team, where he pioneered the dedicated "Rabbit" completion-tester role and quadrupled daily TCR certification throughput from 2–4 games to 8–16 games per day.',
        'Across subsequent tenures at Monolith Productions (triaging 1,300+ weekly tickets and debugging live inside The Matrix Online as a Game Master), Microsoft Game Studios (automating DirectX lab provisioning via PXE/WMI scripts), NVIDIA, and Smartsheet (scaling Karate automation from 0 to 1,500+ tests), Snyder forged a rare combination of hardcore manual playtesting instinct and senior test-framework engineering.',
        'In D:\\DevWorkspace, he brought those two worlds together at full scale: migrating a 50,000-year spherical-globe tactical RPG into Unreal Engine 5.8 C++ backed by 70+ headless C++ tests and 101 Karate E2E scenarios, building the same 1914 WWI aerial physics simulation across Godot 4, Unity 6, and Unreal 5.7, and authoring the Game Forge autonomous pipeline.',
      ],
      motto:
        'Automated headless specs catch the math regressions; an aggressive "Rabbit" playtester with an in-game debug reticle and an Xbox controller catches the lies.',
      stats: [
        { label: 'Game & QA Heritage', value: 'Nintendo · Xbox · MGS · Monolith' },
        { label: 'Xbox TCR Throughput', value: '2–4 → 8–16 Games/Day (4x)' },
        { label: 'Unreal 5.8 C++ Suite', value: '70+ Headless Tests (Exit 0)' },
        { label: 'Karate Gameplay E2E', value: '101 Scenarios · 36 Features' },
        { label: 'Engines Mastered', value: 'UE 5.8 · Unity 6 · Godot 4.5' },
        { label: 'Target Focus', value: '[[COMPANY_NAME]] · [[TARGET_ROLE_TITLE]]' },
      ],
      workspaceChapters: [
        {
          company: 'Multi-Engine Game Forge & TacticalAdberrainUE (D:\\DevWorkspace)',
          position: 'Principal Game Systems, Tooling & QA Architect',
          location: 'Redmond, WA',
          dateSpan: 'Jan 2025 – Present',
          duration: 'Current Frontier',
          tags: ['games', 'unreal-engine', 'unity', 'godot', 'blender', 'automation', 'qa'],
          paragraphs: [
            'To prove that senior SDET discipline and AI-governed toolchains can conquer multi-engine game production, Thomas architected Game Forge alongside flagship simulations in Unreal Engine 5.8 C++ (`TacticalAdberrainUE`), Unreal 5.7 (`WWPatrick`), Unity 6 (`WWUnity`), and Godot 4.5 (`WWGodot`).',
            'When migrating `Tactical-Adberrain` (a multi-generational RPG housing a 68.4 MB D&D 3.5e SQLite rules vault) to Unreal Engine 5.8 C++, subtle coordinate drift and inverted planetary normals initially slipped past naive automated checks. Rather than guessing at fixes, Thomas commissioned in-engine tilde (`~`) diagnostic terminals, live viewport coordinate reticles (`mark_start`), and 70+ native headless Unreal C++ automation tests paired with 101 Karate E2E scenarios.',
            'Similarly, across the 1914 WWI aerial combat trilogy (`WWGodot`, `WWUnity`, `WWPatrick`), he built standalone HTML5 aerodynamic and Web Audio rotary synthesizers before touching runtime engine code, wired Blender 5.2 MCP directly into the asset pipeline, and enforced strict Visual Bar parity against magenta shaders, unreadable light-on-light UI, and uncapped GPU black screens.',
            'This synthesis of classic Xbox "Rabbit" exploratory tenacity with modern C++/C#/Karate automation and MCP editor tooling is purpose-built for [[COMPANY_NAME]].',
          ],
          lesson:
            'In complex 3D games and simulations, never trust a green headless test alone—build in-game coordinate telemetry terminals, standalone balance workbenches, and visual screenshot receipts.',
        },
      ],
    },
    coverLetterConfig: {
      subjectLine: 'Application for [[TARGET_ROLE_TITLE]] — [[COMPANY_NAME]]',
      openingHook:
        'I am writing to apply for the **[[TARGET_ROLE_TITLE]]** role at **[[COMPANY_NAME]]**. My career in games and software quality began on the hardware benches of **Nintendo of America**, **Microsoft Game Studios**, **Monolith Productions**, and the original **Xbox TCR Certification Team**—where I pioneered the dedicated **"Rabbit"** speedrun-completion testing role and helped quadruple our lab’s daily certification throughput from 2–4 titles to 8–16 titles per day.',
      alignmentParagraph:
        'Over the past decade at **OpenMarket** and **Smartsheet**, I scaled that foundational game-testing instinct into enterprise test automation architecture—building a **1,500+ test Karate framework from zero baseline** to replace 85% of manual regression. Today, I combine both halves of that career to build **multi-engine game automation harnesses, custom diagnostic workbenches, and MCP editor pipelines** that directly match your needs for **[[COMPANY_PRODUCT_OR_PLATFORM]]** across **[[JD_PRIMARY_KEYWORD_1]]**, **[[JD_PRIMARY_KEYWORD_2]]**, and **[[JD_PRIMARY_KEYWORD_3]]**:\n\n' +
        '- **Unreal Engine 5.7/5.8 C++ & Multi-Engine QA Harnesses:** Architected **70+ native headless Unreal C++ automation specs** (`EXIT CODE: 0`) and **101 Karate E2E scenarios** for *Tactical-Adberrain* (a spherical hex-globe RPG backed by a 68.4 MB SQLite rules vault), plus built the same 1914 aerial physics simulation across **Unreal 5.7 C++20 (`WWPatrick`)**, **Unity 6 C# (`WWUnity`)**, and **Godot 4.5 (`WWGodot`)**.\n' +
        '- **In-Game Diagnostic Levers & Standalone Workbenches:** Rather than guessing at spatial or physics bugs, I build in-game tilde (`~`) debug terminals, live coordinate targeting reticles (`mark_start`), wingtip telemetry loggers, and standalone HTML5 physics/audio balance simulators.\n' +
        '- **Forensic Visual & Cert Gatekeeping:** Whether catching an inverted-globe sky-fog "soft pass" at 10-mile camera altitude, hunting down magenta URP shaders, or automating PC hardware setups via **WMI/PXE** and **WinDbg**, I ensure broken builds never reach players.',
      differentiatorParagraph:
        'I am an aggressive daily playtester who immediately boots builds in windowed mode with a controller in hand, backed by the architectural depth to design CI/CD gates and **Blender/Unreal/Unity/Godot MCP** pipelines that solve **[[JD_SPECIFIC_CHALLENGE_OR_GOAL]]** for your **[[TEAM_OR_ORG_NAME]]** team.',
      closingParagraph:
        'Thank you for your time and consideration. I would welcome the chance to discuss how my Xbox/Microsoft game QA heritage and modern multi-engine automation tooling can support **[[COMPANY_NAME]]**.',
    },
  },

  // ===========================================================================
  // ROLE 4: R&D / PLATFORM — PRINCIPAL DEVEX & AUTOMATION ARCHITECT
  // ===========================================================================
  {
    id: '04_Principal_DevEx_Automation_Architect',
    roleTitle: 'Principal Developer Experience (DevEx) & Automation Architect',
    targetSector: 'Platform Engineering, Mobile/Web Infrastructure, R&D & Forward-Deployed Teams',
    targetExamples: 'Google, Meta, Stripe, Cloudflare, Zapier, Mobile/Android Platform Teams, High-Growth Scaleups',
    summaryTemplate:
      'Principal Developer Experience (DevEx) and Test Automation Architect with 26+ years of experience eliminating engineering friction, building zero-dependency diagnostic levers, and scaling automated verification across mobile (Android/iOS), web, cloud APIs, and bare-metal hardware labs. Targeted for the [[TARGET_ROLE_TITLE]] role at [[COMPANY_NAME]], bringing proven mastery in [[JD_PRIMARY_KEYWORD_1]], [[JD_PRIMARY_KEYWORD_2]], and [[JD_PRIMARY_KEYWORD_3]]. Known for cutting manual regression cycles by 50%–85% (Smartsheet, Apptio), engineering custom Pure-ADB mobile test harnesses that execute 50% faster than Appium (`karate_androidnow` / `python_androidnow`), and building resilient full-stack developer workbenches and MCP servers.',
    keywordSlotLine:
      '[[JD_PRIMARY_KEYWORD_1]] · [[JD_PRIMARY_KEYWORD_2]] · [[JD_PRIMARY_KEYWORD_3]] · [[JD_PLATFORM_OR_MOBILE_STACK]] · [[JD_DEVEX_METRIC]]',
    prioritizedSkills: [
      {
        name: 'Target Role & Company Alignment (Manual Keyword Zone)',
        level: 'Target Match',
        keywords: [
          '[[JD_PRIMARY_KEYWORD_1]]',
          '[[JD_PRIMARY_KEYWORD_2]]',
          '[[JD_PRIMARY_KEYWORD_3]]',
          '[[JD_PLATFORM_OR_MOBILE_STACK]]',
          '[[JD_CI_CD_OR_INFRA_TOOL]]',
        ],
      },
      {
        name: 'Developer Experience (DevEx), Tooling & Workflow Velocity',
        level: 'Expert',
        keywords: [
          '"Build the Lever" Diagnostic & CLI Tooling Architecture',
          'Copy-Pasteable Developer Test Templates (OpenMarket / Smartsheet)',
          'Zero-Install HTML5 Simulators & Interactive Workbenches',
          'Automated Lab Imaging & Provisioning (PXE / WMI / WTT / Docker)',
          '30-60-90 Day Rapid Stack Assimilation & Documentation Overhauls',
        ],
      },
      {
        name: 'Next-Gen Mobile & Cross-Browser Automation Harnesses',
        level: 'Expert',
        keywords: [
          'Pure-ADB Custom Harnesses (Java `AdbDriver` & Python `uiautomator` XML Parsers)',
          'Jetpack Compose Bounds & Obscure Heuristics ("25% Visibility Rule")',
          'Multi-Threaded `logcat` Event Synchronization (50% Faster than Appium 2)',
          'Playwright (Stealth Contexts, Offline Selector Auditors, Drift Heuristics)',
          'Karate DSL (1,500+ Unified API + UI + Visual Tests)',
        ],
      },
      {
        name: 'Resilient Ingestion, Anti-Bot & Full-Stack Systems',
        level: 'Advanced',
        keywords: [
          'Per-Domain Rate Limiters, Jitter & HTTP 429 Circuit Breakers',
          'Non-Blocking DNS Health Sweepers & Dead-Domain Quarantine',
          'FastAPI / Uvicorn + SQLite / ChromaDB + React / Vite / Tailwind',
          'Node.js ESM Compilers, AJV Schema Validation & Vitest Suites',
          'Model Context Protocol (MCP) Bridges & Agentic Skill Routers',
        ],
      },
      {
        name: 'Cross-Team Enablement & Quality Governance',
        level: 'Expert',
        keywords: [
          'Building QA & DevEx Organizations from 1 Tester to Full Squads (Placed Inc.)',
          'Seamless Offshore & Cross-Time-Zone Scenario Handoffs (Microsoft)',
          'Jenkins / TeamCity / GitHub Actions CI/CD Gatekeeping',
          'MitM Proxy Manipulation, Fiddler & Packet-Level Diagnostics',
        ],
      },
    ],
    featuredProjects: [
      {
        name: 'Now in Android (NiA) Tri-Paradigm Mobile Harness Benchmark (Appium vs. Karate-ADB vs. Python-ADB)',
        url: 'https://github.com/Mr-Thomas-Snyder',
        description:
          'Comparative mobile automation engineering study implementing the exact same 7 E2E scenarios against Google’s Jetpack Compose "Now in Android" app across three distinct harness architectures.',
        highlights: [
          'Engineered `karate_androidnow`: a custom Pure-ADB + Karate DSL driver (`AdbDriver.java` + Jsoup `uiautomator dump` XML bounds parser) that eliminated Appium/Node.js server overhead and cut test execution time by ~50%',
          'Engineered `python_androidnow`: a zero-dependency Python ADB harness implementing the "25% visibility rule" for Jetpack Compose overlays and multi-threaded `logcat` event triggers with sub-second interaction latency and 100% pass rate',
          'Benchmarked both custom levers directly against `appium_androidnow` (Java 17 + Appium 2.x + Allure) to establish empirical mobile DevEx standards',
        ],
        keywords: ['Android ADB', 'Jetpack Compose', 'Java 17', 'Python', 'Karate DSL', 'Appium 2', 'UIAutomator'],
      },
      {
        name: 'TalentScout — Resilient Scraper, Selector Auditor & Resume-as-Code MCP Platform',
        url: 'https://github.com/Saikojin/Talentscout',
        description:
          'Full-stack Python FastAPI + Playwright + Node.js ESM automation platform featuring self-healing DOM scrapers, offline diagnostic CLIs, and a 7-tool TypeScript MCP server.',
        highlights: [
          'Built standalone diagnostic CLI levers (`audit_selectors.py` and `verify_site_health.py`) to benchmark CSS/XPath selectors offline and automatically quarantine dead DNS domains',
          'Implemented semantic DOM drift self-healing (`selector_heuristics.py`) and per-domain HTTP 429 5-minute circuit breakers (`rate_limiter.py`)',
          'Created an AJV schema-validated JSON->MD/HTML/PDF/DOCX compiler and deterministic NLG Career Story engine backed by 38/38 Vitest tests',
        ],
        keywords: ['Python', 'Playwright', 'FastAPI', 'Node.js ESM', 'TypeScript MCP', 'SQLite', 'Vitest'],
      },
      {
        name: 'BookIngestion & ArtistAgent — Multi-Stage Compiler & Local GPU Workbenches',
        url: 'https://github.com/Mr-Thomas-Snyder',
        description:
          '8-stage document structural compiler (`BookIngestion`) and reference-conditioned local GPU asset foundry (`ArtistAgent`) designed to eliminate manual content preparation bottlenecks.',
        highlights: [
          'Built font-size heuristic heading fallback parsers and interactive React/Vite node-graph Blueprint Views for complex PDFs lacking table-of-contents metadata',
          'Engineered PIL color-quantization palette extractors and automated manifest builders driving local SDXL pipelines on 12GB VRAM',
        ],
        keywords: ['FastAPI', 'React / Vite', 'SQLite', 'Python PIL', 'SDXL', 'GGUF'],
      },
    ],
    storyConfig: {
      subtitle: 'The Developer Experience, Mobile Harnesses & Diagnostic Levers Odyssey',
      tagline:
        'Whenever an engineering team is stuck repeating a slow, fragile manual process, don’t just work harder—build the lever that cuts the cycle from hours to minutes.',
      synopsis: [
        'Across 26+ years of software engineering, one pattern has repeated in every organization Thomas S. Snyder has joined: talented developers and testers trapped in soul-crushing manual toil. At Microsoft Game Studios in 2005, engineers were spending hours manually reinstalling Windows and DirectX between game test passes. At Hewlett-Packard in 2009, server lab technicians were installing operating systems by hand after a team consolidation. At Apptio in 2018, Fortune 500 upgrade validations took a full business day of manual clicking. At Smartsheet in 2021, regression testing was 100% manual.',
        'In every single chapter, Snyder’s response was identical: "Build the Lever." He wrote WMI batch scripts and PXE network boot pipelines that cut hours of OS setup down to minutes; he published migration cheat sheets and shortcut maps at Apptio that cut regression time in half; he designed copy-pasteable Karate API templates at OpenMarket that unblocked cloud migration squads; and he built a 1,500-test automation suite at Smartsheet that freed 85% of manual QA capacity.',
        'In D:\\DevWorkspace, that DevEx philosophy reached its pinnacle—producing custom Pure-ADB Android harnesses that run 50% faster than Appium, self-healing Playwright selector auditors, and the 130+ skill SeikoClaw-Harness.',
      ],
      motto:
        'Great Developer Experience is about removing friction at the boundary: replace tribal knowledge with executable templates, and replace slow middleware with lean, deterministic levers.',
      stats: [
        { label: 'DevEx Track Record', value: '26+ Years Building Levers' },
        { label: 'Mobile ADB Speedup', value: '~50% Faster than Appium 2' },
        { label: 'Apptio Regression Cut', value: 'Full Day → Half Day (50%)' },
        { label: 'Smartsheet Automation', value: '0 → 1,500+ Tests (85%)' },
        { label: 'Lab Provisioning', value: 'Hours → Minutes (PXE/WMI)' },
        { label: 'Target Focus', value: '[[COMPANY_NAME]] · [[TARGET_ROLE_TITLE]]' },
      ],
      workspaceChapters: [
        {
          company: 'Tri-Paradigm Mobile Harnesses & DevEx Tooling (D:\\DevWorkspace)',
          position: 'Principal DevEx & Automation Systems Architect',
          location: 'Redmond, WA',
          dateSpan: 'Jan 2025 – Present',
          duration: 'Current Frontier',
          tags: ['devex', 'mobile', 'android', 'automation', 'playwright', 'tooling'],
          paragraphs: [
            'Frustrated by the heavy server overhead, flaky socket timeouts, and slow execution of traditional Appium mobile test suites, Thomas designed a controlled 3-paradigm engineering benchmark against Google’s Jetpack Compose "Now in Android" application (`appium_androidnow`, `karate_androidnow`, and `python_androidnow`).',
            'By building a custom Java `AdbDriver` for Karate DSL and a zero-dependency Python ADB engine that parse `uiautomator dump` XML trees directly, apply a mathematical "25% visibility rule" for overlapping Compose containers, and synchronize on live `logcat` telemetry events, he achieved a 100% pass rate across all 7 E2E user journeys while cutting execution time by ~50% compared to Appium 2.',
            'He applied the exact same "Build the Lever" discipline to web scraping and career tooling in `TalentScout`—authoring an offline Playwright selector auditor (`audit_selectors.py`), a non-blocking DNS dead-domain quarantine sweeper (`verify_site_health.py`), and a heuristic DOM drift self-healing engine (`selector_heuristics.py`).',
            'Whether unblocking mobile CI pipelines, building standalone HTML5 simulation workbenches, or equipping developers with self-service Karate/Playwright templates, these tools demonstrate the immediate DevEx multiplier Thomas brings to [[COMPANY_NAME]].',
          ],
          lesson:
            'When standard frameworks introduce bloat and flakiness, dropping down one layer to the native protocol (ADB, CDP, or raw HTTP/SQLite) yields massive gains in speed and determinism.',
        },
      ],
    },
    coverLetterConfig: {
      subjectLine: 'Application for [[TARGET_ROLE_TITLE]] — [[COMPANY_NAME]]',
      openingHook:
        'I am writing to express my strong interest in the **[[TARGET_ROLE_TITLE]]** position at **[[COMPANY_NAME]]**. Throughout my 26-year career across **Microsoft**, **Smartsheet**, **OpenMarket**, **Placed Inc.**, and **Hewlett-Packard**, my defining engineering reflex has been simple: whenever a team is slowed down by manual toil, flaky middleware, or undocumented tribal knowledge, **I build the reusable lever, template, or automation harness that multiplies team velocity**.',
      alignmentParagraph:
        'Your focus on **[[COMPANY_PRODUCT_OR_PLATFORM]]** and need for strong capabilities in **[[JD_PRIMARY_KEYWORD_1]]**, **[[JD_PRIMARY_KEYWORD_2]]**, and **[[JD_PRIMARY_KEYWORD_3]]** align directly with the developer productivity and automation systems I have delivered:\n\n' +
        '- **50%–85% Cycle-Time Reductions in Production (Smartsheet, OpenMarket & Apptio):** Built Smartsheet’s **Karate DSL** automation suite from a zero baseline to **1,500+ tests (85% manual regression coverage)**; designed copy-pasteable API testing templates at OpenMarket that accelerated company-wide **AWS** microservice onboarding; and cut Fortune 500 upgrade validation cycles in half at Apptio.\n' +
        '- **Next-Gen Mobile & Web DevEx Harnesses (`karate_androidnow`, `python_androidnow` & `TalentScout`):** Engineered custom **Pure-ADB + XML bounds + `logcat`** test harnesses for Jetpack Compose that execute **~50% faster than Appium 2** with zero Node.js server overhead, alongside offline **Playwright** selector auditors, HTTP 429 circuit breakers, and semantic DOM drift self-healing.\n' +
        '- **Bare-Metal & CI/CD Infrastructure Scaling (Placed Inc., Microsoft & HP):** Scaled Placed Inc.’s QA organization from a single tester to a full multi-platform (Web/iOS/Android/Jenkins/MitM) team, and built **PXE/WMI/WTT** automated lab imaging pipelines at Microsoft and HP that reduced machine provisioning from hours to minutes.',
      differentiatorParagraph:
        'In addition, I created **SeikoClaw-Harness** (a 130+ skill AI engineering harness) and multiple **Model Context Protocol (MCP)** servers to bring deterministic guardrails and verification receipts to AI-assisted development—positioning me to immediately tackle **[[JD_SPECIFIC_CHALLENGE_OR_GOAL]]** for the **[[TEAM_OR_ORG_NAME]]** team.',
      closingParagraph:
        'I would welcome the opportunity to discuss how my "Build the Lever" engineering approach and 26 years of cross-stack automation leadership can accelerate developer velocity at **[[COMPANY_NAME]]**.',
    },
  },
];

// ─────────────────────────────────────────────────────────────────────────────
// BUILD ROLE-TAILORED RESUME JSON
// ─────────────────────────────────────────────────────────────────────────────
function buildRoleResumeData(roleSpec) {
  const cloned = JSON.parse(JSON.stringify(baseResume));
  cloned.basics.label = `${roleSpec.roleTitle} — Target: [[COMPANY_NAME]]`;
  cloned.basics.summary = roleSpec.summaryTemplate;
  cloned.skills = roleSpec.prioritizedSkills;
  cloned.projects = roleSpec.featuredProjects;
  cloned.keywordSlotLine = roleSpec.keywordSlotLine;
  return cloned;
}

// ─────────────────────────────────────────────────────────────────────────────
// GENERATE RESUME MARKDOWN (FOR ANY ATS STYLE OR STANDARD)
// ─────────────────────────────────────────────────────────────────────────────
function generateRoleResumeMarkdown(resumeData, roleSpec, atsStyle = null) {
  const { basics, work, education, skills, projects } = resumeData;
  const lines = [];

  lines.push(`# ${basics.name}`);
  lines.push(`**${roleSpec.roleTitle}**`);
  lines.push(`*Target Application: [[TARGET_ROLE_TITLE]] at [[COMPANY_NAME]]*`);
  lines.push('');
  lines.push(
    `${basics.email} · ${basics.location.city}, ${basics.location.region} ${basics.location.postalCode} · [LinkedIn](${basics.url}) · [GitHub (Mr-Thomas-Snyder)](https://github.com/Mr-Thomas-Snyder) · [GitHub (Saikojin)](https://github.com/Saikojin/seikoclaw-harness)`
  );
  lines.push('');

  lines.push('> ### 🎯 Manual Keyword & Role Alignment Zone (Replace `[[...]]` Before Sending)');
  lines.push(`> - **Target Company & Role:** \`[[COMPANY_NAME]]\` — \`[[TARGET_ROLE_TITLE]]\``);
  lines.push(`> - **Priority JD Keywords:** ${roleSpec.keywordSlotLine}`);
  lines.push('');

  lines.push('## Executive Summary');
  lines.push(basics.summary);
  lines.push('');

  lines.push('## Core Competencies & Technical Skills');
  for (const s of skills) {
    lines.push(`- **${s.name}** *(${s.level})*: ${s.keywords.join(' · ')}`);
  }
  lines.push('');

  if (projects?.length) {
    lines.push('## Flagship Systems & Architecture Portfolio (`D:\\DevWorkspace`)');
    for (const p of projects) {
      lines.push(`### ${p.name}`);
      lines.push(p.description);
      for (const h of p.highlights || []) {
        lines.push(`- ${h}`);
      }
      if (p.keywords?.length) {
        lines.push(`- *Technologies:* ${p.keywords.join(', ')}`);
      }
      lines.push('');
    }
  }

  lines.push(
    atsStyle
      ? `## Professional Experience (${atsStyle} ATS Framework Edition)`
      : '## Professional Experience (26-Year Career Record)'
  );

  for (const job of work) {
    const startFmt = job.startDate ? job.startDate.slice(0, 7).replace('-', '/') : '';
    const endFmt = job.endDate ? job.endDate.slice(0, 7).replace('-', '/') : 'Present';
    lines.push(`### ${job.name} — ${job.position} (${job.location || 'Redmond/Seattle, WA'})`);
    lines.push(`*${startFmt} – ${endFmt}*`);
    if (job.summary) lines.push(job.summary);
    lines.push('');

    if (atsStyle) {
      const bullets = formatWorkEntryAts(job, atsStyle);
      for (const b of bullets) {
        lines.push(`- ${b}`);
      }
    } else {
      for (const h of job.highlights || []) {
        lines.push(`- ${h}`);
      }
      if (job.wins?.length) {
        lines.push('  - **Key Wins:** ' + job.wins.join(' | '));
      }
      if (job.toolsUsed?.length) {
        lines.push('  - **Tools & Stack:** ' + job.toolsUsed.join(' · '));
      }
    }
    lines.push('');
  }

  if (education?.length) {
    lines.push('## Education & Continuous Technical Development');
    for (const edu of education) {
      lines.push(`### ${edu.studyType} — ${edu.area}`);
      lines.push(`*${edu.institution}*`);
      for (const c of edu.courses || []) {
        lines.push(`- ${c}`);
      }
      lines.push('');
    }
  }

  return lines.join('\n');
}

// ─────────────────────────────────────────────────────────────────────────────
// GENERATE RESUME DOCX (WITH HIGHLIGHTED [[...]] SLOTS + ATS STYLE SUPPORT)
// ─────────────────────────────────────────────────────────────────────────────
async function generateRoleResumeDocx(resumeData, roleSpec, outputPath, atsStyle = null) {
  const { basics, work, education, skills, projects } = resumeData;
  const children = [];

  const addSectionHeading = (title) => {
    children.push(
      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 260, after: 100 },
        border: {
          bottom: { color: '0f3460', space: 4, style: BorderStyle.SINGLE, size: 8 },
        },
        children: [
          new TextRun({
            text: title.toUpperCase(),
            bold: true,
            size: 22,
            font: 'Arial',
            color: '0f3460',
          }),
        ],
      })
    );
  };

  const addBullet = (text, level = 0) => {
    children.push(
      new Paragraph({
        bullet: { level },
        spacing: { after: 45 },
        children: parseHighlightedRuns(text, { font: 'Arial', size: 19, color: '1e293b' }),
      })
    );
  };

  // Header: Name
  children.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 40 },
      children: [
        new TextRun({
          text: basics.name,
          bold: true,
          size: 36,
          font: 'Arial',
          color: '0f3460',
        }),
      ],
    })
  );

  // Header: Role Title
  children.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 60 },
      children: parseHighlightedRuns(
        `${roleSpec.roleTitle}  |  Target: [[COMPANY_NAME]] ([[TARGET_ROLE_TITLE]])`,
        { font: 'Arial', size: 20, italics: true, bold: true, color: '334155' }
      ),
    })
  );

  // Header: Contact
  children.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 180 },
      children: [
        new TextRun({
          text: `${basics.email}  |  ${basics.location.city}, ${basics.location.region}  |  ${basics.url}  |  github.com/Saikojin/seikoclaw-harness`,
          size: 18,
          font: 'Arial',
          color: '475569',
        }),
      ],
    })
  );

  // Marked Keyword Insertion Box
  children.push(
    new Paragraph({
      spacing: { before: 60, after: 160 },
      border: {
        top: { color: 'd97706', space: 4, style: BorderStyle.SINGLE, size: 6 },
        bottom: { color: 'd97706', space: 4, style: BorderStyle.SINGLE, size: 6 },
        left: { color: 'd97706', space: 8, style: BorderStyle.SINGLE, size: 18 },
        right: { color: 'd97706', space: 4, style: BorderStyle.SINGLE, size: 6 },
      },
      shading: { type: ShadingType.CLEAR, fill: 'fffbeb' },
      children: [
        new TextRun({
          text: 'TARGET ROLE KEYWORD SLOTS (Replace Yellow [[...]] Tags Before Submitting): ',
          bold: true,
          size: 18,
          font: 'Arial',
          color: '92400e',
        }),
        ...parseHighlightedRuns(roleSpec.keywordSlotLine, {
          font: 'Arial',
          size: 18,
          color: '1e293b',
        }),
      ],
    })
  );

  // Executive Summary
  addSectionHeading('Executive Summary');
  children.push(
    new Paragraph({
      spacing: { after: 160 },
      children: parseHighlightedRuns(basics.summary, {
        font: 'Arial',
        size: 19,
        color: '1e293b',
      }),
    })
  );

  // Core Competencies & Skills
  addSectionHeading('Core Competencies & Technical Skills');
  for (const skill of skills) {
    children.push(
      new Paragraph({
        spacing: { after: 65 },
        children: [
          new TextRun({
            text: `${skill.name}: `,
            bold: true,
            size: 19,
            font: 'Arial',
            color: '0f3460',
          }),
          ...parseHighlightedRuns(skill.keywords.join(' · '), {
            font: 'Arial',
            size: 19,
            color: '1e293b',
          }),
        ],
      })
    );
  }

  // Flagship Engineering Systems & Projects
  if (projects?.length) {
    addSectionHeading('Flagship Engineering Systems & Tooling (D:\\DevWorkspace)');
    for (const proj of projects) {
      children.push(
        new Paragraph({
          spacing: { before: 120, after: 40 },
          children: [
            new TextRun({
              text: proj.name,
              bold: true,
              size: 20,
              font: 'Arial',
              color: '0f3460',
            }),
            proj.keywords?.length
              ? new TextRun({
                  text: `  [${proj.keywords.join(', ')}]`,
                  italics: true,
                  size: 18,
                  font: 'Arial',
                  color: '64748b',
                })
              : new TextRun({ text: '' }),
          ],
        })
      );
      children.push(
        new Paragraph({
          spacing: { after: 50 },
          children: parseHighlightedRuns(proj.description, {
            font: 'Arial',
            size: 19,
            italics: true,
            color: '334155',
          }),
        })
      );
      for (const h of proj.highlights || []) {
        addBullet(h);
      }
    }
  }

  // Professional Experience
  addSectionHeading(
    atsStyle
      ? `Professional Experience (${atsStyle} ATS Framework)`
      : 'Professional Experience'
  );

  for (const job of work) {
    const startFmt = job.startDate ? job.startDate.slice(0, 7).replace('-', '/') : '';
    const endFmt = job.endDate ? job.endDate.slice(0, 7).replace('-', '/') : 'Present';
    const dateStr = `${startFmt} – ${endFmt}`;

    children.push(
      new Paragraph({
        spacing: { before: 150, after: 30 },
        tabStops: [{ type: 'right', position: 9020 }],
        children: [
          new TextRun({
            text: `${job.name}  —  ${job.position}`,
            bold: true,
            size: 21,
            font: 'Arial',
            color: '0f3460',
          }),
          new TextRun({
            text: `\t${job.location ? job.location + '  |  ' : ''}${dateStr}`,
            size: 18,
            font: 'Arial',
            color: '64748b',
          }),
        ],
      })
    );

    if (job.summary) {
      children.push(
        new Paragraph({
          spacing: { after: 60 },
          children: [
            new TextRun({
              text: job.summary,
              italics: true,
              size: 18,
              font: 'Arial',
              color: '475569',
            }),
          ],
        })
      );
    }

    if (atsStyle) {
      const atsBullets = formatWorkEntryAts(job, atsStyle);
      for (const b of atsBullets) {
        addBullet(b);
      }
    } else {
      for (const h of job.highlights || []) {
        addBullet(h);
      }
      if (job.wins?.length) {
        children.push(
          new Paragraph({
            spacing: { before: 40, after: 30 },
            children: [
              new TextRun({ text: 'Key Wins: ', bold: true, size: 18, font: 'Arial', color: '0f3460' }),
              new TextRun({ text: job.wins.join(' · '), size: 18, font: 'Arial', color: '1e293b' }),
            ],
          })
        );
      }
      if (job.toolsUsed?.length) {
        children.push(
          new Paragraph({
            spacing: { after: 50 },
            children: [
              new TextRun({ text: 'Tools Used: ', bold: true, size: 18, font: 'Arial', color: '334155' }),
              new TextRun({ text: job.toolsUsed.join(' · '), size: 18, font: 'Arial', color: '475569' }),
            ],
          })
        );
      }
    }
  }

  // Education
  if (education?.length) {
    addSectionHeading('Education & Professional Development');
    for (const edu of education) {
      children.push(
        new Paragraph({
          spacing: { before: 100, after: 40 },
          children: [
            new TextRun({
              text: `${edu.institution}  —  ${edu.studyType}: ${edu.area}`,
              bold: true,
              size: 19,
              font: 'Arial',
              color: '0f3460',
            }),
          ],
        })
      );
      for (const c of edu.courses || []) {
        addBullet(c);
      }
    }
  }

  const doc = new Document({
    creator: basics.name,
    title: `${basics.name} — ${roleSpec.roleTitle} (${atsStyle || 'Standard'})`,
    description: `Tailored ${roleSpec.roleTitle} Resume for ${basics.name}`,
    sections: [
      {
        properties: {
          page: {
            margin: { top: 720, right: 800, bottom: 720, left: 800 },
          },
        },
        children,
      },
    ],
  });

  const buffer = await Packer.toBuffer(doc);
  writeFileSync(outputPath, buffer);
}

// ─────────────────────────────────────────────────────────────────────────────
// GENERATE COVER LETTER (.MD & .DOCX WITH MARKED KEYWORD SLOTS)
// ─────────────────────────────────────────────────────────────────────────────
function generateRoleCoverLetterMarkdown(resumeData, roleSpec) {
  const { basics } = resumeData;
  const cl = roleSpec.coverLetterConfig;

  return `# ${basics.name}
**${roleSpec.roleTitle}**  
${basics.location.city}, ${basics.location.region} ${basics.location.postalCode} · ${basics.email} · [LinkedIn](${basics.url}) · [GitHub](https://github.com/Saikojin/seikoclaw-harness)

---

> ### ✏️ Manual Keyword & Company Fill-In Checklist
> Replace these bracketed tokens before sending (use \`Ctrl+H\` in Word or Markdown):
> 1. \`[[COMPANY_NAME]]\` — Target company name *(e.g., ${roleSpec.targetExamples.split(',').slice(0, 3).join(',')})*
> 2. \`[[TARGET_ROLE_TITLE]]\` — Exact job title from the posting *(default: ${roleSpec.roleTitle})*
> 3. \`[[COMPANY_PRODUCT_OR_PLATFORM]]\` — Specific product, platform, or initiative mentioned in the JD
> 4. \`[[JD_PRIMARY_KEYWORD_1]]\` — Top technical skill/requirement #1 from JD
> 5. \`[[JD_PRIMARY_KEYWORD_2]]\` — Top technical skill/requirement #2 from JD
> 6. \`[[JD_PRIMARY_KEYWORD_3]]\` — Top technical skill/requirement #3 from JD
> 7. \`[[JD_SPECIFIC_CHALLENGE_OR_GOAL]]\` — Core team pain point or 12-month goal in the JD
> 8. \`[[TEAM_OR_ORG_NAME]]\` — Name of the hiring team or engineering division

---

**Date:** [[APPLICATION_DATE]]

**To:** Hiring Team — [[TEAM_OR_ORG_NAME]]  
**Company:** [[COMPANY_NAME]]  
**Subject:** ${cl.subjectLine}

Dear [[COMPANY_NAME]] Hiring Team,

${cl.openingHook}

${cl.alignmentParagraph}

${cl.differentiatorParagraph}

**Additional Role-Specific Alignment Notes:**
- **Core Stack & Keywords Matched:** [[JD_PRIMARY_KEYWORD_1]], [[JD_PRIMARY_KEYWORD_2]], [[JD_PRIMARY_KEYWORD_3]], [[ADDITIONAL_JD_KEYWORDS_HERE]]
- **Immediate 30-60-90 Day Focus for [[COMPANY_NAME]]:** [[OPTIONAL_CUSTOM_SENTENCE_FOR_COMPANY_INITIATIVE]]

${cl.closingParagraph}

Sincerely,

**${basics.name}**  
${roleSpec.roleTitle}  
${basics.email}  
${basics.url}
`;
}

async function generateRoleCoverLetterDocx(resumeData, roleSpec, outputPath) {
  const { basics } = resumeData;
  const cl = roleSpec.coverLetterConfig;
  const children = [];

  // Header
  children.push(
    new Paragraph({
      spacing: { after: 40 },
      children: [
        new TextRun({
          text: basics.name,
          bold: true,
          size: 32,
          font: 'Arial',
          color: '0f3460',
        }),
      ],
    })
  );

  children.push(
    new Paragraph({
      spacing: { after: 40 },
      children: parseHighlightedRuns(`${roleSpec.roleTitle}  —  Target: [[TARGET_ROLE_TITLE]]`, {
        font: 'Arial',
        size: 20,
        bold: true,
        color: '334155',
      }),
    })
  );

  children.push(
    new Paragraph({
      spacing: { after: 160 },
      border: {
        bottom: { color: 'cbd5e1', space: 6, style: BorderStyle.SINGLE, size: 6 },
      },
      children: [
        new TextRun({
          text: `${basics.location.city}, ${basics.location.region} ${basics.location.postalCode}  |  ${basics.email}  |  ${basics.url}  |  github.com/Saikojin/seikoclaw-harness`,
          size: 18,
          font: 'Arial',
          color: '475569',
        }),
      ],
    })
  );

  // Instruction Box for Manual Keywords
  const checklistItems = [
    '[[COMPANY_NAME]] — Target company name',
    '[[TARGET_ROLE_TITLE]] — Exact job posting title',
    '[[COMPANY_PRODUCT_OR_PLATFORM]] — Target product, service, or game title',
    '[[JD_PRIMARY_KEYWORD_1]], [[JD_PRIMARY_KEYWORD_2]], [[JD_PRIMARY_KEYWORD_3]] — Top 3 required skills from JD',
    '[[JD_SPECIFIC_CHALLENGE_OR_GOAL]] — Key problem or milestone described in JD',
    '[[TEAM_OR_ORG_NAME]] — Hiring team or engineering org name',
  ];

  children.push(
    new Paragraph({
      spacing: { before: 60, after: 60 },
      shading: { type: ShadingType.CLEAR, fill: 'fffbeb' },
      children: [
        new TextRun({
          text: 'MANUAL KEYWORD FILL-IN GUIDE (Delete this box after replacing yellow [[...]] tags):',
          bold: true,
          size: 18,
          font: 'Arial',
          color: '92400e',
        }),
      ],
    })
  );

  for (const item of checklistItems) {
    children.push(
      new Paragraph({
        bullet: { level: 0 },
        spacing: { after: 30 },
        shading: { type: ShadingType.CLEAR, fill: 'fffbeb' },
        children: parseHighlightedRuns(item, { font: 'Arial', size: 17, color: '334155' }),
      })
    );
  }

  // Date & Addressee
  children.push(
    new Paragraph({
      spacing: { before: 200, after: 80 },
      children: parseHighlightedRuns('Date: [[APPLICATION_DATE]]', {
        font: 'Arial',
        size: 20,
        color: '1e293b',
      }),
    })
  );

  children.push(
    new Paragraph({
      spacing: { after: 40 },
      children: parseHighlightedRuns('To: Hiring Team — [[TEAM_OR_ORG_NAME]] at [[COMPANY_NAME]]', {
        font: 'Arial',
        size: 20,
        bold: true,
        color: '1e293b',
      }),
    })
  );

  children.push(
    new Paragraph({
      spacing: { after: 160 },
      children: parseHighlightedRuns(`RE: ${cl.subjectLine}`, {
        font: 'Arial',
        size: 20,
        bold: true,
        color: '0f3460',
      }),
    })
  );

  // Salutation
  children.push(
    new Paragraph({
      spacing: { after: 120 },
      children: parseHighlightedRuns('Dear [[COMPANY_NAME]] Hiring Team,', {
        font: 'Arial',
        size: 20,
        color: '1e293b',
      }),
    })
  );

  // Body Paragraphs
  const cleanMdBold = (str) => str.replace(/\*\*/g, '');

  children.push(
    new Paragraph({
      spacing: { after: 140 },
      children: parseHighlightedRuns(cleanMdBold(cl.openingHook), {
        font: 'Arial',
        size: 20,
        color: '1e293b',
      }),
    })
  );

  const alignLines = cl.alignmentParagraph.split('\n').filter((l) => l.trim());
  for (const line of alignLines) {
    if (line.startsWith('- ')) {
      children.push(
        new Paragraph({
          bullet: { level: 0 },
          spacing: { after: 80 },
          children: parseHighlightedRuns(cleanMdBold(line.slice(2)), {
            font: 'Arial',
            size: 19,
            color: '1e293b',
          }),
        })
      );
    } else {
      children.push(
        new Paragraph({
          spacing: { after: 100 },
          children: parseHighlightedRuns(cleanMdBold(line), {
            font: 'Arial',
            size: 20,
            color: '1e293b',
          }),
        })
      );
    }
  }

  children.push(
    new Paragraph({
      spacing: { before: 80, after: 140 },
      children: parseHighlightedRuns(cleanMdBold(cl.differentiatorParagraph), {
        font: 'Arial',
        size: 20,
        color: '1e293b',
      }),
    })
  );

  // Dedicated Keyword Insertion Block
  children.push(
    new Paragraph({
      spacing: { before: 60, after: 60 },
      children: [
        new TextRun({
          text: 'Targeted Technical & Domain Alignment for ',
          bold: true,
          size: 19,
          font: 'Arial',
          color: '0f3460',
        }),
        ...parseHighlightedRuns('[[COMPANY_NAME]]:', {
          font: 'Arial',
          size: 19,
          bold: true,
          color: '0f3460',
        }),
      ],
    })
  );

  children.push(
    new Paragraph({
      bullet: { level: 0 },
      spacing: { after: 50 },
      children: parseHighlightedRuns(
        'Matched Core Competencies: [[JD_PRIMARY_KEYWORD_1]] · [[JD_PRIMARY_KEYWORD_2]] · [[JD_PRIMARY_KEYWORD_3]] · [[ADDITIONAL_JD_KEYWORDS_HERE]]',
        { font: 'Arial', size: 19, color: '1e293b' }
      ),
    })
  );

  children.push(
    new Paragraph({
      bullet: { level: 0 },
      spacing: { after: 140 },
      children: parseHighlightedRuns(
        'Direct Impact Focus: [[OPTIONAL_CUSTOM_SENTENCE_FOR_COMPANY_INITIATIVE]]',
        { font: 'Arial', size: 19, color: '1e293b' }
      ),
    })
  );

  children.push(
    new Paragraph({
      spacing: { after: 160 },
      children: parseHighlightedRuns(cleanMdBold(cl.closingParagraph), {
        font: 'Arial',
        size: 20,
        color: '1e293b',
      }),
    })
  );

  // Sign-off
  children.push(
    new Paragraph({
      spacing: { after: 80 },
      children: [new TextRun({ text: 'Sincerely,', size: 20, font: 'Arial', color: '1e293b' })],
    })
  );

  children.push(
    new Paragraph({
      spacing: { after: 30 },
      children: [
        new TextRun({
          text: basics.name,
          bold: true,
          size: 22,
          font: 'Arial',
          color: '0f3460',
        }),
      ],
    })
  );

  children.push(
    new Paragraph({
      children: [
        new TextRun({
          text: `${roleSpec.roleTitle}  |  ${basics.email}`,
          size: 19,
          font: 'Arial',
          color: '475569',
        }),
      ],
    })
  );

  const doc = new Document({
    creator: basics.name,
    title: `${basics.name} — Cover Letter (${roleSpec.roleTitle})`,
    sections: [
      {
        properties: {
          page: {
            margin: { top: 900, right: 900, bottom: 900, left: 900 },
          },
        },
        children,
      },
    ],
  });

  const buffer = await Packer.toBuffer(doc);
  writeFileSync(outputPath, buffer);
}

// ─────────────────────────────────────────────────────────────────────────────
// GENERATE ROLE-TAILORED CAREER STORY (.MD, .HTML, .DOCX)
// ─────────────────────────────────────────────────────────────────────────────
function generateRoleStoryData(resumeData, roleSpec) {
  const sc = roleSpec.storyConfig;
  const workEntries = [...(resumeData.work || [])].sort((a, b) =>
    (a.startDate || '').localeCompare(b.startDate || '')
  );

  const careerChapters = workEntries.map((job, idx) => {
    const startYear = job.startDate ? job.startDate.slice(0, 7) : '';
    const endYear = job.endDate ? job.endDate.slice(0, 7) : 'Present';
    const challenge = job.challenges?.[0] || job.keyResponsibilities?.[0] || '';
    const secondaryChallenge = job.challenges?.[1] || job.keyResponsibilities?.[1] || '';
    const tools = (job.toolsUsed || []).slice(0, 5).join(', ');
    const skills = (job.skillsUsed || []).slice(0, 3).join(', ');
    const win1 = job.wins?.[0] || job.highlights?.[0] || '';
    const win2 = job.wins?.[1] || job.highlights?.[1] || '';
    const lesson = job.lessonsLearned?.[0] || '';

    const p1 = `In ${startYear}, Thomas S. Snyder joined ${job.name} as ${job.position} (${job.location || 'Redmond/Seattle, WA'}). ${job.summary || ''}`;
    const p2 = `The operational crucible centered on ${challenge ? challenge.charAt(0).toLowerCase() + challenge.slice(1) : 'elevating system reliability'}.${secondaryChallenge ? ' Compounding this challenge was ' + secondaryChallenge.charAt(0).toLowerCase() + secondaryChallenge.slice(1) + '.' : ''} To address this systematically, Thomas anchored his technical execution in ${tools || 'targeted diagnostic tooling'}, applying deep expertise in ${skills || 'quality engineering'}.`;
    const p3 = `The breakthrough delivered measurable impact: ${win1 ? win1.charAt(0).toLowerCase() + win1.slice(1) : 'key quality milestones were achieved'}.${win2 ? ' Furthermore, ' + win2.charAt(0).toLowerCase() + win2.slice(1) + '.' : ''}`;

    return {
      chapterNumber: idx + 1,
      company: job.name,
      position: job.position,
      location: job.location || 'WA',
      dateSpan: `${startYear} – ${endYear}`,
      paragraphs: [p1, p2, p3],
      lesson,
    };
  });

  // Append Workspace Frontier Chapter(s) as the climax of the story
  const wsChapters = (sc.workspaceChapters || []).map((wch, idx) => ({
    chapterNumber: careerChapters.length + idx + 1,
    company: wch.company,
    position: wch.position,
    location: wch.location,
    dateSpan: wch.dateSpan,
    paragraphs: wch.paragraphs,
    lesson: wch.lesson,
  }));

  return {
    candidateName: resumeData.basics.name,
    roleTitle: roleSpec.roleTitle,
    targetSector: roleSpec.targetSector,
    subtitle: sc.subtitle,
    tagline: sc.tagline,
    synopsis: sc.synopsis,
    motto: sc.motto,
    stats: sc.stats,
    chapters: [...careerChapters, ...wsChapters],
  };
}

function generateRoleStoryMarkdown(storyData) {
  const lines = [];
  lines.push(`# ${storyData.candidateName} — ${storyData.subtitle}`);
  lines.push(`*Role Edition: ${storyData.roleTitle} (${storyData.targetSector})*`);
  lines.push('');
  lines.push('---');
  lines.push('');
  lines.push('## 📕 Back of the Book');
  lines.push(`> *"${storyData.tagline}"*`);
  lines.push('');
  for (const p of storyData.synopsis) {
    lines.push(p);
    lines.push('');
  }
  lines.push(`> 💡 **Core Mantra:** "${storyData.motto}"`);
  lines.push('');
  lines.push('### Edition Specs & Vital Metrics');
  for (const st of storyData.stats) {
    lines.push(`- **${st.label}:** ${st.value}`);
  }
  lines.push('');
  lines.push('---');
  lines.push('');

  for (const ch of storyData.chapters) {
    lines.push(`## Chapter ${ch.chapterNumber}: ${ch.company} (${ch.dateSpan})`);
    lines.push(`**${ch.position}** — *${ch.location}*`);
    lines.push('');
    for (const p of ch.paragraphs) {
      lines.push(p);
      lines.push('');
    }
    if (ch.lesson) {
      lines.push(`> 💡 **Core Takeaway:** "${ch.lesson}"`);
      lines.push('');
    }
    lines.push('---');
    lines.push('');
  }

  lines.push('## Epilogue: Ready for [[COMPANY_NAME]]');
  lines.push(
    `Across ${storyData.chapters.length} chapters spanning console hardware labs, enterprise cloud microservices, and autonomous AI agent harnesses, the governing principle remains constant: build the diagnostic lever first, automate the repetitive 85%, and never accept a "soft pass" without runtime receipts. Next chapter: **[[TARGET_ROLE_TITLE]]** at **[[COMPANY_NAME]]**.`
  );
  lines.push('');

  return lines.join('\n');
}

async function generateRoleStoryDocx(storyData, outputPath) {
  const children = [];

  children.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 60 },
      children: [
        new TextRun({
          text: `${storyData.candidateName} — ${storyData.subtitle}`,
          bold: true,
          size: 32,
          font: 'Arial',
          color: '0f3460',
        }),
      ],
    })
  );

  children.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 200 },
      children: [
        new TextRun({
          text: `Role Edition: ${storyData.roleTitle} (${storyData.targetSector})`,
          italics: true,
          size: 20,
          font: 'Arial',
          color: '475569',
        }),
      ],
    })
  );

  // Back of the Book Box
  children.push(
    new Paragraph({
      heading: HeadingLevel.HEADING_2,
      spacing: { before: 120, after: 100 },
      children: [
        new TextRun({
          text: 'BACK OF THE BOOK — EXECUTIVE SYNOPSIS',
          bold: true,
          size: 24,
          font: 'Arial',
          color: 'b45309',
        }),
      ],
    })
  );

  children.push(
    new Paragraph({
      spacing: { after: 120 },
      shading: { type: ShadingType.CLEAR, fill: 'f8fafc' },
      children: [
        new TextRun({
          text: `“${storyData.tagline}”`,
          italics: true,
          bold: true,
          size: 21,
          font: 'Arial',
          color: '0f3460',
        }),
      ],
    })
  );

  for (const p of storyData.synopsis) {
    children.push(
      new Paragraph({
        spacing: { after: 120 },
        children: parseHighlightedRuns(p, { font: 'Arial', size: 20, color: '1e293b' }),
      })
    );
  }

  children.push(
    new Paragraph({
      spacing: { before: 60, after: 160 },
      shading: { type: ShadingType.CLEAR, fill: 'fffbeb' },
      children: [
        new TextRun({
          text: 'Core Mantra: ',
          bold: true,
          size: 19,
          font: 'Arial',
          color: '92400e',
        }),
        new TextRun({
          text: `“${storyData.motto}”`,
          italics: true,
          size: 19,
          font: 'Arial',
          color: '1e293b',
        }),
      ],
    })
  );

  // Chapters
  for (const ch of storyData.chapters) {
    children.push(
      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 240, after: 40 },
        border: {
          bottom: { color: 'cbd5e1', space: 4, style: BorderStyle.SINGLE, size: 6 },
        },
        children: [
          new TextRun({
            text: `Chapter ${ch.chapterNumber}: ${ch.company} (${ch.dateSpan})`,
            bold: true,
            size: 22,
            font: 'Arial',
            color: '0f3460',
          }),
        ],
      })
    );

    children.push(
      new Paragraph({
        spacing: { after: 80 },
        children: [
          new TextRun({
            text: `${ch.position} — ${ch.location}`,
            bold: true,
            italics: true,
            size: 19,
            font: 'Arial',
            color: '475569',
          }),
        ],
      })
    );

    for (const p of ch.paragraphs) {
      children.push(
        new Paragraph({
          spacing: { after: 100 },
          children: parseHighlightedRuns(p, { font: 'Arial', size: 19, color: '1e293b' }),
        })
      );
    }

    if (ch.lesson) {
      children.push(
        new Paragraph({
          spacing: { after: 120 },
          shading: { type: ShadingType.CLEAR, fill: 'f0f9ff' },
          children: [
            new TextRun({
              text: 'Core Takeaway: ',
              bold: true,
              size: 18,
              font: 'Arial',
              color: '0369a1',
            }),
            new TextRun({
              text: `“${ch.lesson}”`,
              italics: true,
              size: 18,
              font: 'Arial',
              color: '0f172a',
            }),
          ],
        })
      );
    }
  }

  const doc = new Document({
    creator: storyData.candidateName,
    title: `${storyData.candidateName} — ${storyData.subtitle}`,
    sections: [
      {
        properties: {
          page: {
            margin: { top: 800, right: 850, bottom: 800, left: 850 },
          },
        },
        children,
      },
    ],
  });

  const buffer = await Packer.toBuffer(doc);
  writeFileSync(outputPath, buffer);
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN EXECUTION
// ─────────────────────────────────────────────────────────────────────────────
async function main() {
  if (!existsSync(OUT_BASE)) {
    mkdirSync(OUT_BASE, { recursive: true });
  }

  const ATS_STYLES = ['CAR', 'STAR', 'LPS', 'ELITE', 'WHO'];
  let totalFiles = 0;

  console.log('🚀 Building Role Packages across 4 Mapped Engineering Archetypes...\n');

  for (const roleSpec of ROLE_PACKAGES) {
    const roleDir = resolve(OUT_BASE, roleSpec.id);
    if (!existsSync(roleDir)) {
      mkdirSync(roleDir, { recursive: true });
    }

    console.log(`📂 [${roleSpec.id}] — ${roleSpec.roleTitle}`);
    const roleResume = buildRoleResumeData(roleSpec);

    // Save role-specific resume.json + Greenhouse & Workday ATS JSON profiles
    writeFileSync(resolve(roleDir, 'resume_role.json'), JSON.stringify(roleResume, null, 2), 'utf8');
    const [firstName, ...lastParts] = (roleResume.basics?.name ?? 'Thomas S. Snyder').split(' ');
    const greenhouseProfile = {
      first_name: firstName,
      last_name: lastParts.join(' '),
      target_role: roleSpec.roleTitle,
      target_company_slot: '[[COMPANY_NAME]]',
      email_addresses: [{ value: roleResume.basics?.email, type: 'personal' }],
      employments: (roleResume.work ?? []).map((job) => ({
        company_name: job.name,
        title: job.position,
        start_date: job.startDate,
        end_date: job.endDate || null,
        body: [job.summary, ...formatWorkEntryAts(job, 'CAR')].filter(Boolean).join('\n- '),
      })),
      custom_fields: {
        skills_summary: (roleResume.skills ?? []).map((s) => `${s.name}: ${s.keywords.join(', ')}`).join(' | '),
        notable_projects: (roleResume.projects ?? []).map((p) => p.name).join(', '),
      },
    };
    const workdayProfile = {
      legalName: { firstName, lastName: lastParts.join(' '), formattedName: roleResume.basics?.name },
      targetRole: roleSpec.roleTitle,
      targetCompanySlot: '[[COMPANY_NAME]]',
      summary: roleResume.basics?.summary,
      workExperience: (roleResume.work ?? []).map((job) => ({
        employer: job.name,
        jobTitle: job.position,
        startDate: job.startDate,
        endDate: job.endDate || null,
        description: job.summary,
        achievements_STAR: formatWorkEntryAts(job, 'STAR'),
        achievements_CAR: formatWorkEntryAts(job, 'CAR'),
      })),
      skills: (roleResume.skills ?? []).map((s) => ({
        skillCategory: s.name,
        proficiencyLevel: s.level,
        skillKeywords: s.keywords,
      })),
    };
    writeFileSync(resolve(roleDir, 'ATS_Greenhouse_Profile.json'), JSON.stringify(greenhouseProfile, null, 2), 'utf8');
    writeFileSync(resolve(roleDir, 'ATS_Workday_Profile.json'), JSON.stringify(workdayProfile, null, 2), 'utf8');
    totalFiles += 3;

    // 1. Career Story (.md, .html, .docx)
    const storyData = generateRoleStoryData(roleResume, roleSpec);
    const storyMd = generateRoleStoryMarkdown(storyData);
    writeFileSync(resolve(roleDir, 'Career_Story.md'), storyMd, 'utf8');
    writeFileSync(
      resolve(roleDir, 'Career_Story.html'),
      generateStoryHtml(storyMd, `${roleResume.basics.name} — ${roleSpec.roleTitle}`),
      'utf8'
    );
    await generateRoleStoryDocx(storyData, resolve(roleDir, 'Career_Story.docx'));
    totalFiles += 3;
    console.log('   ✅ Career_Story (.md, .html, .docx)');

    // 2. Cover Letter with Marked Keyword Insertion Zones (.md, .docx)
    const coverMd = generateRoleCoverLetterMarkdown(roleResume, roleSpec);
    writeFileSync(resolve(roleDir, 'Cover_Letter.md'), coverMd, 'utf8');
    await generateRoleCoverLetterDocx(roleResume, roleSpec, resolve(roleDir, 'Cover_Letter.docx'));
    totalFiles += 2;
    console.log('   ✅ Cover_Letter (.md, .docx) [with highlighted [[...]] keyword slots]');

    // 3. Standard Clean ATS Resume (.md, .docx)
    const stdMd = generateRoleResumeMarkdown(roleResume, roleSpec, null);
    writeFileSync(resolve(roleDir, 'Resume_Standard.md'), stdMd, 'utf8');
    await generateRoleResumeDocx(roleResume, roleSpec, resolve(roleDir, 'Resume_Standard.docx'), null);
    totalFiles += 2;
    console.log('   ✅ Resume_Standard (.md, .docx)');

    // 4. All 5 Known ATS Framework Styles (CAR, STAR, LPS, ELITE, WHO) in .md and .docx
    for (const style of ATS_STYLES) {
      const styleMd = generateRoleResumeMarkdown(roleResume, roleSpec, style);
      writeFileSync(resolve(roleDir, `Resume_ATS_${style}.md`), styleMd, 'utf8');
      await generateRoleResumeDocx(
        roleResume,
        roleSpec,
        resolve(roleDir, `Resume_ATS_${style}.docx`),
        style
      );
      totalFiles += 2;
    }
    console.log(`   ✅ ATS Framework Resumes (.md, .docx): ${ATS_STYLES.join(', ')}\n`);
  }

  console.log(`🎉 Successfully generated ${totalFiles} files across 4 Role Packages in:`);
  console.log(`   ${OUT_BASE}`);
}

main().catch((err) => {
  console.error('❌ Failed to build role packages:', err);
  process.exit(1);
});
