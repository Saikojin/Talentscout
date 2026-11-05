#!/usr/bin/env node
/**
 * resume/compiler/buildMicrosoftDossier.js
 * Generates the complete executive deliverables for the Microsoft Quality Leadership dossier:
 * 1. 01_Cross_Quadrant_Telemetry_Blueprint (.md, .docx, .pdf)
 * 2. 02_Chaos_Injection_Matrix_Fault_Tolerance_Spec (.md, .docx, .pdf)
 * 3. 03_Senior_Technical_Competency_Portfolio (.md, .docx, .pdf)
 */

import { writeFileSync, existsSync, mkdirSync, readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { marked } from 'marked';
import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  AlignmentType,
  BorderStyle,
  Table,
  TableRow,
  TableCell,
  WidthType,
  ShadingType,
  Header,
  Footer,
  PageNumber
} from 'docx';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, '..', '..');
const OUT_DIR = resolve(ROOT, 'tailored_outputs', 'Microsoft_Principal_QA_Architect');

if (!existsSync(OUT_DIR)) {
  mkdirSync(OUT_DIR, { recursive: true });
}

// Common styles for HTML -> PDF
function getHtmlWrapper(title, bodyHtml) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>${title}</title>
  <style>
    @page {
      size: letter;
      margin: 20mm 20mm 20mm 20mm;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #1e293b;
      line-height: 1.55;
      font-size: 10pt;
      margin: 0;
      padding: 0;
    }
    h1 {
      color: #0f172a;
      font-size: 20pt;
      border-bottom: 2px solid #0284c7;
      padding-bottom: 6px;
      margin-top: 0;
      margin-bottom: 12px;
      line-height: 1.2;
    }
    h2 {
      color: #0369a1;
      font-size: 14pt;
      border-bottom: 1px solid #cbd5e1;
      padding-bottom: 4px;
      margin-top: 18px;
      margin-bottom: 8px;
      page-break-after: avoid;
    }
    h3 {
      color: #0f172a;
      font-size: 11pt;
      margin-top: 14px;
      margin-bottom: 6px;
      page-break-after: avoid;
    }
    p {
      margin-top: 0;
      margin-bottom: 8px;
    }
    ul, ol {
      margin-top: 0;
      margin-bottom: 8px;
      padding-left: 20px;
    }
    li {
      margin-bottom: 4px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 12px 0;
      font-size: 9pt;
      page-break-inside: avoid;
    }
    th, td {
      border: 1px solid #cbd5e1;
      padding: 6px 8px;
      text-align: left;
      vertical-align: top;
    }
    th {
      background-color: #f1f5f9;
      color: #0f172a;
      font-weight: 600;
    }
    tr:nth-child(even) td {
      background-color: #f8fafc;
    }
    blockquote {
      border-left: 4px solid #0284c7;
      background: #f0f9ff;
      margin: 12px 0;
      padding: 8px 12px;
      color: #0369a1;
      font-style: italic;
    }
    code {
      background: #f1f5f9;
      padding: 2px 4px;
      border-radius: 3px;
      font-family: Consolas, "Courier New", monospace;
      font-size: 9pt;
      color: #0f172a;
    }
    pre {
      background: #0f172a;
      color: #f8fafc;
      padding: 10px;
      border-radius: 4px;
      font-family: Consolas, "Courier New", monospace;
      font-size: 8.5pt;
      overflow-x: auto;
      margin: 10px 0;
    }
    pre code {
      background: transparent;
      color: inherit;
      padding: 0;
    }
    .header-box {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 10px 14px;
      margin-bottom: 16px;
      font-size: 9pt;
    }
    .header-box table {
      margin: 0;
      border: none;
    }
    .header-box td {
      border: none;
      padding: 2px 6px;
      background: transparent !important;
    }
  </style>
</head>
<body>
  ${bodyHtml}
</body>
</html>`;
}

async function renderPdf(htmlContent, outputPath) {
  const { default: puppeteer } = await import('puppeteer');
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  await page.setContent(htmlContent, { waitUntil: 'networkidle0' });
  const pdfBuffer = await page.pdf({
    format: 'Letter',
    margin: { top: '15mm', right: '15mm', bottom: '15mm', left: '15mm' },
    printBackground: true,
    displayHeaderFooter: true,
    headerTemplate: '<div></div>',
    footerTemplate: '<div style="font-size:8pt; text-align:right; width:100%; padding-right:15mm; color:#94a3b8;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>'
  });
  await browser.close();
  writeFileSync(outputPath, pdfBuffer);
}

// ─────────────────────────────────────────────────────────────────────────────
// DOCUMENT DEFINITIONS
// ─────────────────────────────────────────────────────────────────────────────

const DOC_1_MD = `# Cross-Quadrant Telemetry & Observability Blueprint
**Correlating Silicon & Kernel Infrastructure to High-Scale SaaS Application Reliability**

> **Author:** Thomas S. Snyder  
> **Role Target:** Strategic Quality Leadership / Enterprise Cloud Portfolio — Microsoft  
> **Candidate Background:** 26+ Years Software Quality Engineering (5 tenures at Microsoft, Smartsheet, OpenMarket, Xbox TCR)  
> **Classification:** Executive Architecture Specification & Telemetry Framework  

---

## 1. Executive Summary & Problem Formulation

In high-scale distributed cloud platforms, traditional monitoring suffers from the **"Siloed Observability Fallacy."** Infrastructure teams monitor CPU, memory, and hypervisor health; network engineers monitor switch fabrics and socket buffers; microservice teams track gRPC error rates; and product teams track SaaS p99 latency and front-end synthetic transactions.

Because these telemetry streams exist in isolated operational quadrants, degradation events manifest as **ghost failures**:
1. Micro-burst packet loss or NIC ring buffer overflows in the hypervisor show up as intermittent 2.5s tail latency spikes in SaaS checkout workflows.
2. Kernel context-switch thrashing under specific CPU microcode thermal states triggers silent WebSocket dropouts without throwing application exceptions.
3. Database connection pools experience thread pool starvation due to OS-level ephemeral port exhaustion, yet the database reports normal query execution times.

This blueprint establishes a **Cross-Quadrant Telemetry & Observability Plane** designed to ingest, normalize, and causally correlate signals from bare-metal silicon and OS kernels directly to SaaS customer-journey metrics. By operationalizing this cross-layer correlation, engineering teams transition from reactive postmortem triage to **preemptive, automated failure deflection 30 to 120 seconds before customer SLO breach**.

---

## 2. The Four Observability Quadrants

The enterprise stack is partitioned into four distinct telemetry quadrants, each characterized by its capture frequency, transport mechanism, and operational ownership:

\`\`\`
+-----------------------------------------------------------------------------------+
|                            THE 4 OBSERVABILITY QUADRANTS                         |
+-----------------------------------------------------------------------------------+
|  QUADRANT I: SILICON & HARDWARE           |  QUADRANT II: OS KERNEL & RUNTIME     |
|  - PCIe bus CRC errors                   |  - Windows ETW / Linux eBPF probes    |
|  - NIC ring buffer drops & interrupts     |  - WinDbg kernel memory crash dumps   |
|  - CPU C-state & thermal throttles        |  - TCP socket backlog & syn-flood state|
|  - NVMe queue depth & write stalls        |  - Thread pool starvation & cgroup mem|
+-------------------------------------------+---------------------------------------+
|  QUADRANT III: DISTRIBUTED SERVICES       |  QUADRANT IV: SAAS EXPERIENCE         |
|  - OpenTelemetry W3C distributed traces   |  - Real-User Monitoring (RUM) metrics |
|  - gRPC/REST response code distribution   |  - Synthetic transactional journeys   |
|  - Envoy/service mesh sidecar latency     |  - Client UI thread stall (>50ms)     |
|  - Kafka/Service Bus lag & backpressure   |  - Business funnel conversion drop    |
+-----------------------------------------------------------------------------------+
\`\`\`

### Quadrant I: Silicon & Physical Infrastructure
- **Metrics Collected:** Bare-metal CPU package temperatures, frequency throttling flags, PCIe uncorrectable error counts, NIC rx_dropped/tx_dropped packets, NVMe write latency spikes.
- **Capture Seams:** IPMI, Baseboard Management Controllers (BMC), vendor hardware lab monitoring tools (leveraging Windows Hardware Lab Kit / HLK and WTT test bed automation).

### Quadrant II: OS Kernel & Container Runtime
- **Metrics Collected:** Windows Event Tracing for Windows (ETW), Linux eBPF probe telemetry, kernel thread context switches, TCP retransmission timeouts (RTO), container cgroup CPU throttle quotas, socket file descriptor exhaustion.
- **Capture Seams:** WinDbg symbol-connected dump analyzers, eBPF daemonsets, OS performance counter drivers.

### Quadrant III: Distributed Microservices & Transport Mesh
- **Metrics Collected:** Ingestion API latency (p50, p95, p99), gRPC status codes (DEADLINE_EXCEEDED, RESOURCE_EXHAUSTED), Kafka/Azure Service Bus partition offset lag, circuit breaker state changes (Closed -> Open), service mesh proxy overhead.
- **Capture Seams:** OpenTelemetry SDK collectors, Envoy sidecar telemetry, custom Karate/BDD integration test probes.

### Quadrant IV: High-Level SaaS Application & User Experience
- **Metrics Collected:** Synthetic end-to-end transaction latency, client-side browser DOM render stalls (>50ms frame drops), API error budget burn rate, user session abort rates.
- **Capture Seams:** Playwright headless probes, BrowserStack synthetic nodes, RUM client telemetry tokens.

---

## 3. Cross-Quadrant Telemetry Correlation Architecture

Connecting kernel interrupts to SaaS user transactions requires an end-to-end telemetry pipeline that guarantees zero loss and deterministic causality.

\`\`\`
+-------------------+       +--------------------+       +----------------------+
|  SaaS Client App  | ----> | Ingestion Gateway  | ----> | Microservice Mesh    |
|  (Quadrant IV)    |       | (Quadrant III)     |       | (Quadrant III)       |
+-------------------+       +--------------------+       +----------------------+
         |                            |                             |
  Injects W3C Trace            Binds Pod cgroup             Binds OS Thread / Socket
  & Session Token              & Hypervisor ID              & Kernel FD
         v                            v                             v
+-------------------------------------------------------------------------------+
|             CROSS-QUADRANT CORRELATION BUS (Kafka / OpenTelemetry)           |
|     Stitches: [TraceId] <-> [Pod/ContainerId] <-> [NodeId] <-> [Core/NIC]     |
+-------------------------------------------------------------------------------+
                                      |
                                      v
+-------------------------------------------------------------------------------+
|                 PREEMPTIVE SYSTEMIC ANOMALY ENGINE (ML / Heuristic)           |
|  - Detects hardware/kernel degradation 30-120s before customer impact        |
|  - Triggers automated circuit shedding and pod eviction                      |
+-------------------------------------------------------------------------------+
\`\`\`

### 3.1 Trace Context Propagation (The Correlation Thread)
Every inbound customer request is assigned an immutable W3C \`traceparent\` header upon entering the edge gateway. As the request descends through the microservice topology, the gateway and sidecars append physical execution metadata:
\`\`\`json
{
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "quadrant_context": {
    "q4_client": { "client_type": "web_desktop", "synthetic": false, "geo": "us-west-2" },
    "q3_service": { "service_name": "billing-orchestrator", "pod_id": "billing-prod-7f89c" },
    "q2_kernel": { "node_id": "k8s-node-az-104", "tid": 18422, "tcp_rto_events": 3 },
    "q1_silicon": { "rack_id": "puget-core-r12", "cpu_socket": 1, "nic_ring_drops": 42 }
  }
}
\`\`\`

### 3.2 Temporal Lag Correlation
Hardware and kernel issues do not instantaneously crash application APIs; they cause queuing and backpressure that ripple upwards over 15 to 90 seconds. 
- **Lead Indicator:** Quadrant I NIC ring buffer packet drop rate rises by >12%.
- **Secondary Indicator (T+15s):** Quadrant II TCP retransmit rates and context switches surge on the affected host.
- **Downstream Impact (T+45s):** Quadrant III microservice connection pool exhausts available sockets, causing gRPC queue delays.
- **Customer Symptom (T+75s):** Quadrant IV SaaS p99 latency breaches 2,000ms threshold, tripping SLO alarms.

By training anomaly detectors on this temporal chain, the telemetry engine alerts on the **Lead Indicator**, enabling automatic remediation before the Customer Symptom ever occurs.

---

## 4. Preemptive Failure Detection & Automated Mitigation Engine

When correlation metrics identify systemic failure patterns, the system executes an automated mitigation protocol:

| Severity Level | Lead Indicator (Q1/Q2) | Lag Indicator (Q3/Q4) | Automated Mitigation Action |
|---|---|---|---|
| **Tier 1: Minor Degrade** | Node CPU thermal throttle >15% or single NIC drop spike | API p95 latency elevates <10% | Soft traffic bleed: stop scheduling new pods on node; shift non-critical background jobs. |
| **Tier 2: Host Saturation** | Kernel socket buffer allocation >85% or cgroup memory pressure | Microservice connection queue depth doubling | Canary drain: mark node Unschedulable; cordon and drain active pods with graceful 15s SIGTERM. |
| **Tier 3: Systemic Core Failure** | PCIe bus fatal errors or kernel uncorrectable panic | Downstream API p99 latency breaches 1,500ms | Hard circuit trip: failover all regional ingress traffic to secondary availability zone; trigger WinDbg crash dump capture. |

---

## 5. Implementation Roadmap & QA Governance

Drawing upon 26 years of quality engineering across Microsoft OS compatibility labs, Xbox TCR, and modern SaaS ecosystems:

1. **Sprint 1–3 (Foundation):** Standardize OpenTelemetry collectors across all services; deploy eBPF kernel telemetry daemonsets across cluster nodes.
2. **Sprint 4–6 (Correlation Plane):** Implement unified trace tagging linking pod identifiers to underlying host hardware metrics in Azure Monitor / Splunk.
3. **Sprint 7–9 (Preemptive Policies):** Validate automated canary drain policies using automated chaos injection; certify that zero 5xx errors leak to users during host drainage.
4. **Sprint 10+ (Enterprise Maturity):** Integrate telemetry-driven quality gates directly into Azure DevOps CI/CD pipelines to block builds showing abnormal kernel syscall distributions.
`;

const DOC_2_MD = `# CI/CD Chaos Injection Matrix & Fault-Tolerance Specification
**Operationalizing the "Garbage In, Garbage Out" Doctrine Across Distributed Microservices**

> **Author:** Thomas S. Snyder  
> **Role Target:** Strategic Quality Leadership / Enterprise Cloud Portfolio — Microsoft  
> **Candidate Background:** 26+ Years Software Quality Engineering (5 tenures at Microsoft, Smartsheet, OpenMarket, Xbox TCR)  
> **Classification:** Engineering Test Specification & Resiliency Gate Contract  

---

## 1. Specification Scope & Engineering Doctrine

The core tenet of robust software architecture is simple: **"Garbage In, Garbage Out" (GIGO)**. A fragile system attempts to process corrupt, boundary-exceeding, or delayed input, leading to thread deadlocks, memory leaks, unhandled exceptions, and cascading cross-service failure. A resilient system identifies garbage at the boundary, rejects it deterministically, degrades gracefully, and maintains unbroken uptime for unaffected workloads.

This specification details the **CI/CD Chaos Injection Matrix**: an automated testing framework integrated into staging and release pipelines that systematically attacks microservice boundaries with malicious, malformed, and hostile stimuli.

---

## 2. The 5-Vector Automated Chaos Matrix

The matrix tests five fundamental attack vectors across service boundaries, asserting strict mathematical pass/fail contracts:

| Vector | Injected Fault Scenario | Boundary Under Test | Expected Graceful Degradation | Automated Pass/Fail Gate |
|---|---|---|---|---|
| **Vector 1: Malformed Payloads & Boundary Fuzzing ("Garbage In")** | Truncated JSON/Protobuf, boundary integer overflows (\\(-1\\), \\(2^{63}-1\\)), null-byte injections, schema drift, illegal UTF-8 | API Gateway, Deserialization Middleware, Data Ingestion Layer | Immediate deterministic HTTP 400/422 response; structured error schema; zero unhandled null pointer or memory panics; zero service restarts | 100% rejection rate of malformed payloads; zero pod restarts; memory delta \\(\\le 2\\%\\) |
| **Vector 2: Network Degradation & MitM Jitter** | Injected latency (200ms–2500ms jitter), 10%–30% packet loss, TCP reset during TLS handshake, connection half-close | Inter-service transport, Envoy proxy mesh, external API egress | Client timeouts enforced at 1200ms SLA; cached read fallback; exponential backoff with randomized jitter; zero socket pool exhaustion | Zero connection pool starvation; circuit breakers report Healthy or Half-Open; zero unhandled socket timeouts |
| **Vector 3: Cascading Dependency Death & Blackholing** | Upstream Authentication service or primary database drops to 0% availability (HTTP 503, dropped SYN, infinite wait) | Ingress Gateway, Service Mesh Circuit Breaker | Circuit breaker trips from Closed to Open after 3 failed probes; service serves cached/stale data or fallback UI; zero thread starvation downstream | Downstream services maintain \\(\\ge 99.9\\%\\) availability; failover completes in \\(\\le 2.0\\) seconds |
| **Vector 4: Ephemeral Resource Starvation** | Container CPU throttle (100% busy spin injection), memory ballooning to cgroup limit, disk IOPS exhaustion on log volumes | Kubernetes Kubelet, Pod Resource Scheduler | Kubernetes Readiness probe fails, removing pod from load balancer; pod recycles cleanly via Liveness probe without corrupting in-flight transactions | Zero 5xx errors served to end users; horizontal pod autoscaler (HPA) schedules new replica within 45s |
| **Vector 5: Token & Security Entropy** | Expired JWTs, signature tampering, cross-tenant ID injection, replay nonce reuse, malformed bearer headers | OAuth2 / OIDC Middleware, API Gateway Edge | Immediate deterministic HTTP 401/403 rejection at outer perimeter; security incident audit event logged; zero downstream microservices invoked | Zero internal compute cycles wasted; zero sensitive trace leakage in error response |

---

## 3. Detailed Fault Injection Methodology

### 3.1 Vector 1: Boundary Fuzzing & Malformed Ingestion ("Garbage In")
Building on 26 years of test automation (including 1,500 Karate automated test suites at Smartsheet and SMS/MMS protocol fuzzing at OpenMarket):
- **Automated Ingestion Tests:** Every endpoint is bombarded with edge-case matrices:
  - Numeric boundary violations: \\(0\\), \\(-1\\), \\(2^{31}-1\\), \\(2^{63}-1\\), \\(\\text{NaN}\\), \\(\\infty\\).
  - String boundary violations: Empty strings, 1MB string buffers, SQL injection strings, null characters (\`\\0\`), RTL overrides.
  - Structural boundary violations: Deeply nested JSON arrays (>100 levels) to test parser stack depth.
- **Contract Gate:** The service must return a standardized RFC-7807 Problem Details JSON within 50ms, recording zero memory leak in the process runtime.

### 3.2 Vector 2: Man-in-the-Middle (MitM) & Network Degradation
Drawing on physical lab and proxy manipulation experience (Placed Inc., AT&T Faraday chambers, and Nokia mobile rigs):
- **Implementation:** Ephemeral proxy sidecars inject artificial TCP window shrinkage, packet duplication, and latency spikes directly into inter-service gRPC calls.
- **Contract Gate:** Upstream callers must abort the stalled request upon hitting the timeout deadline (e.g. 1,200ms) and release the HTTP/2 stream multiplexer immediately.

### 3.3 Vector 3: Cascading Failure & Bulkhead Isolation
- **Implementation:** Synthetic "black hole" mock services simulate a hung dependency that accepts TCP connections but never sends an ACK or data byte.
- **Contract Gate:** Bulkhead thread pools must isolate the hung service. Other routes in the same microservice must continue responding with normal p50 latencies (<15ms).

---

## 4. CI/CD Pipeline Integration & Blast Radius Containment

To ensure that chaos injection creates release confidence rather than production outages, the execution follows strict environmental isolation:

\`\`\`
+-----------------------+      +-----------------------+      +-----------------------+
|  Pull Request Stage   | ---> | Staging Chaos Suite   | ---> | Canary Traffic Gate   |
|  - Unit & Karate BDD  |      | - 5-Vector Injection  |      | - 2% Production Split |
|  - Zero-Tolerance lint|      | - Synthetic tenant    |      | - Continuous Telemetry|
+-----------------------+      +-----------------------+      +-----------------------+
                                           |                              |
                                   Abort Tripwire:                Rollback Tripwire:
                                 Staging Error > 1.0%           Error Budget Burn > 0.1%
\`\`\`

1. **Synthetic Isolation:** Chaos injection runs exclusively against dedicated synthetic tenant accounts (\`tenant_id: synthetic_chaos_*\`). Shared database rows and cache keys are strictly namespace-isolated.
2. **Automated Abort Tripwires:** If non-synthetic tenant traffic experiences any elevated latency or if the overall staging error rate exceeds 1.0%, the test harness triggers an immediate SIGKILL on the chaos agents and restores baseline routing.
3. **Release Gate Artifact:** Every CI/CD run generates an auditable **Resiliency Attestation Certificate**, confirming that the build withstood all 5 chaos vectors without human intervention.
`;

const DOC_3_MD = `# Senior Technical Competency & Adaptability Portfolio
**The 30-60-90 Day Field-Tested Quality Engineering Framework**

> **Author:** Thomas S. Snyder  
> **Role Target:** Strategic Quality Leadership / Enterprise Cloud Portfolio — Microsoft  
> **Candidate Background:** 26+ Years Software Quality Engineering (5 tenures at Microsoft, Smartsheet, OpenMarket, Xbox TCR)  
> **Classification:** Executive Leadership Dossier & Practical Methodology Framework  

---

## 1. Executive Perspective: Field-Tested Mastery vs Traditional Certifications

Traditional software testing certifications (e.g., ISTQB, CSTE) serve a purpose in establishing shared vocabulary. However, when an enterprise engineering organization faces high-velocity cloud migrations, microservice race conditions, and legacy test suite decay, **theoretical taxonomy does not ship software**.

Over a 26-year career spanning 5 tenures at Microsoft, enterprise SaaS leaders like Smartsheet, high-throughput cloud infrastructure at OpenMarket, and console hardware ecosystems at Xbox, true quality leadership has always been defined by three practical realities:
1. **Ruthless Pragmatism ("Most Bang for the Buck"):** Identifying the 15% of critical customer workflows that represent 80% of business and revenue risk, and automating them with ironclad reliability.
2. **Zero-Baseline Velocity:** The ability to enter an organization with zero existing automation, entrenched manual testing resistance, or decaying legacy scripts, and deliver production-grade automated suites within weeks.
3. **Deep Diagnostic Curiosity:** Bridging high-level API behavior with white-box system diagnostics—from WinDbg stack trace analysis and kernel crash dumps to proxy manipulation and distributed trace correlation.

---

## 2. The 30-60-90 Day Rapid Assimilation Framework

When dropped into an ambiguous, fast-moving, or unfamiliar product team, this proven 3-phase framework establishes immediate quality visibility, stabilizes release confidence, and accelerates automation ROI:

\`\`\`
+---------------------------------------------------------------------------------------+
|                       THE 30-60-90 DAY RAPID ASSIMILATION PLAYBOOK                     |
+---------------------------------------------------------------------------------------+
|  DAYS 1-30: DIAGNOSTIC AUDIT & "RABBIT" EXPLORATION                                    |
|  - Audit existing test suites: classify Signal vs Flaky Debt vs Dead Weight           |
|  - Map architectural seams: interview Dev, PM, and Support to locate unwritten rules  |
|  - The "Rabbit" Run: pioneer exploit-driven speedrun completion passes on core flows   |
+---------------------------------------------------------------------------------------+
|  DAYS 31-60: HIGH-ROI AUTOMATION STRIKE ("MOST BANG FOR THE BUCK")                     |
|  - Build/extend lightweight, robust automation harness (Karate DSL / Playwright)      |
|  - Automate the top 15% core revenue paths from zero to 100% deterministic coverage    |
|  - Embed non-flaky quality gates into PR/CI pipelines with clean-slate execution      |
+---------------------------------------------------------------------------------------+
|  DAYS 61-90: PRACTICE ELEVATION, STANDARDIZATION & CULTURAL SCALE                     |
|  - Distribute reusable API & scenario test templates across feature engineering teams  |
|  - Mentor junior/mid QA engineers; transition manual testers into automation authors   |
|  - Establish executive Quality KPIs: Defect Escape Rate, MTTD, Flake Ratio            |
+---------------------------------------------------------------------------------------+
\`\`\`

### Phase 1: Days 1–30 — The Diagnostic Audit & "Rabbit" Exploration
- **Test Suite Audit & Flake Quarantine:** Categorize all existing automated tests into three buckets:
  1. *High-Signal Core:* Tests that reliably catch regressions. Protect and prioritize.
  2. *Flaky / High-Maintenance Debt:* Tests failing due to timing, test-order coupling, or shared test-bed state. Immediately quarantine them out of the blocking PR gate to restore developer trust in CI.
  3. *Dead Weight:* Obsolete tests verifying deprecated behavior. Delete them ruthlessly.
- **Cross-Discipline Seam Mapping:** Bridge the gap between engineering, product, and customer support (leveraging the Bug Association Representative / BAR methodology created at Monolith Productions). Uncover undocumented customer pain points that never appear in formal requirement tickets.
- **The "Rabbit" Exploratory Pass:** Originated by Thomas Snyder during his tenure on Xbox at VMC/Microsoft, the "Rabbit" methodology designates a senior quality engineer to execute unscripted, exploit-seeking, speedrun-style end-to-end sessions across complete application workflows. This rapidly uncovers systemic bottlenecks, hard-locks, and boundary crashes before automation design begins.

### Phase 2: Days 31–60 — The High-ROI Automation Strike
- **Framework Architecture:** Deploy a zero-friction, highly readable automation framework (e.g., Karate DSL for API/microservices or Playwright for web UI) that requires minimal boilerplate and supports parallel execution.
- **The 80/20 Coverage Strike:** Avoid attempting to automate 100% of legacy edge cases. Target the core transaction engine, auth boundary, and data persistence layers—achieving immediate 80%+ regression coverage on high-risk paths.
- **Pipeline Quality Gates:** Integrate test runs directly into CI/CD build definitions. Enforce the **Clean Slate Rule**: tests must dynamically spin up or isolate their own test data, execute deterministically, and tear down without leaving orphaned database state.

### Phase 3: Days 61–90 — Practice Elevation & Cultural Scale
- **Reusable Engineering Templates:** Package successful test patterns into modular, copy-pasteable templates for developers and QA engineers (the OpenMarket and Microsoft Compatibility playbook).
- **Mentorship & Empowerment:** Conduct pairing sessions with junior and mid-level engineers, demystifying automation frameworks and teaching exploratory heuristics.
- **Metrics That Matter:** Implement quality dashboards reporting on actionable engineering metrics:
  - *Mean Time to Detect (MTTD)* & *Defect Escape Rate (DER)*.
  - *Automation Pass Confidence Rate* (percentage of pipeline runs completing without flake).
  - *Engineering Hours Reclaimed* from manual regression passes.

---

## 3. Verified Field Case Studies & Historical Proof Points

### Case Study A: Smartsheet (Zero-to-85% Karate Automation)
- **Challenge:** Software test engineering team relied on manual passes for complex Drupal-based web portals and custom apps. Entrenched resistance to automation; zero test automation baseline.
- **Action:** Championed and architected a comprehensive Karate DSL automation framework from scratch. Authored 1,500 automated tests covering API, UI, and performance validation. Integrated cross-browser testing via BrowserStack.
- **Outcome:** Replaced 85% of manual testing workload with continuous automation. Freed up extensive QA capacity, enabling the team to focus on advanced exploratory testing and winning deep trust from product leadership.

### Case Study B: OpenMarket (Cloud Microservices Migration & QA Standardization)
- **Challenge:** High-volume telecom microservices processing billions of SMS, MMS, and RCS messages undergoing major cloud migration to AWS. Outdated, undocumented Fit/Fitnesse legacy tests; lack of cross-team QA standards.
- **Action:** Transitioned testing infrastructure to Karate DSL. Designed reusable API testing templates distributed to cloud migration teams. Rewrote missing codebase documentation to serve as product Subject Matter Expert.
- **Outcome:** Standardized QA methodologies across distributed feature teams, accelerated cloud cutovers, and ensured zero message drop during AWS migration.

### Case Study C: Microsoft Windows OS & Xbox (Hardware Compatibility & The "Rabbit" Role)
- **Challenge:** At Microsoft (Windows Compatibility STE3), pre-release hardware (ARM boards, IoT, unreleased GPUs) caused frequent lab provisioning bottlenecks and kernel-level crashes. On Xbox (VMC/Microsoft), Technical Certification Requirements (TCR) testing throughput was constrained to only 2–4 games per day.
- **Action:** Developed WTT automated test beds and PXE network imaging infrastructure. Utilized WinDbg on symbol-connected builds to isolate kernel stack crashes. On Xbox, pioneered the dedicated "Rabbit" speedrun completion role and established rotating multi-shift testing passes.
- **Outcome:** Quadrupled Xbox TCR throughput from 2–4 games/day to 8–16 games/day. At Windows OS, automated OS flashing saved days of preparation time and enabled overnight hardware compatibility sweeps across hundreds of physical devices.
`;

// ─────────────────────────────────────────────────────────────────────────────
// BUILD DOCX LOGIC
// ─────────────────────────────────────────────────────────────────────────────

function createDocxDocument(title, sections) {
  const children = [];

  // Title Header
  children.push(
    new Paragraph({
      heading: HeadingLevel.TITLE,
      alignment: AlignmentType.CENTER,
      spacing: { before: 200, after: 100 },
      children: [
        new TextRun({
          text: title,
          bold: true,
          size: 32,
          font: 'Segoe UI',
          color: '0f172a'
        })
      ]
    })
  );

  // Metadata Subtitle Box
  children.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 280 },
      children: [
        new TextRun({
          text: 'Author: Thomas S. Snyder  |  Target: Microsoft Enterprise Quality Leadership  |  26+ Years Experience',
          italics: true,
          size: 19,
          font: 'Segoe UI',
          color: '0369a1'
        })
      ]
    })
  );

  for (const sec of sections) {
    // Heading 1
    if (sec.h1) {
      children.push(
        new Paragraph({
          heading: HeadingLevel.HEADING_1,
          spacing: { before: 280, after: 120 },
          border: {
            bottom: { color: '0284c7', space: 4, style: BorderStyle.SINGLE, size: 12 }
          },
          children: [
            new TextRun({
              text: sec.h1,
              bold: true,
              size: 26,
              font: 'Segoe UI',
              color: '0284c7'
            })
          ]
        })
      );
    }

    // Heading 2
    if (sec.h2) {
      children.push(
        new Paragraph({
          heading: HeadingLevel.HEADING_2,
          spacing: { before: 200, after: 80 },
          children: [
            new TextRun({
              text: sec.h2,
              bold: true,
              size: 22,
              font: 'Segoe UI',
              color: '0f172a'
            })
          ]
        })
      );
    }

    // Paragraphs
    if (sec.p) {
      for (const text of sec.p) {
        children.push(
          new Paragraph({
            spacing: { after: 100 },
            children: [
              new TextRun({
                text,
                size: 20,
                font: 'Segoe UI',
                color: '334155'
              })
            ]
          })
        );
      }
    }

    // Callout / Blockquote
    if (sec.quote) {
      children.push(
        new Paragraph({
          spacing: { before: 100, after: 120 },
          border: {
            left: { color: '0284c7', space: 8, style: BorderStyle.SINGLE, size: 24 }
          },
          shading: { type: ShadingType.CLEAR, fill: 'f0f9ff' },
          children: [
            new TextRun({
              text: `  ${sec.quote}`,
              italics: true,
              size: 20,
              font: 'Segoe UI',
              color: '0369a1'
            })
          ]
        })
      );
    }

    // Bullet points
    if (sec.bullets) {
      for (const b of sec.bullets) {
        children.push(
          new Paragraph({
            bullet: { level: 0 },
            spacing: { after: 60 },
            children: [
              new TextRun({
                text: b,
                size: 20,
                font: 'Segoe UI',
                color: '1e293b'
              })
            ]
          })
        );
      }
    }

    // Table
    if (sec.table) {
      const rows = [];
      // Header row
      rows.push(
        new TableRow({
          children: sec.table.headers.map(
            (h) =>
              new TableCell({
                shading: { type: ShadingType.CLEAR, fill: '0f172a' },
                children: [
                  new Paragraph({
                    children: [
                      new TextRun({
                        text: h,
                        bold: true,
                        size: 18,
                        font: 'Segoe UI',
                        color: 'ffffff'
                      })
                    ]
                  })
                ]
              })
          )
        })
      );

      // Data rows
      for (const r of sec.table.rows) {
        rows.push(
          new TableRow({
            children: r.map(
              (cellText, idx) =>
                new TableCell({
                  shading: { type: ShadingType.CLEAR, fill: idx % 2 === 0 ? 'f8fafc' : 'ffffff' },
                  children: [
                    new Paragraph({
                      children: [
                        new TextRun({
                          text: cellText,
                          size: 17,
                          font: 'Segoe UI',
                          color: '1e293b'
                        })
                      ]
                    })
                  ]
                })
            )
          })
        );
      }

      children.push(
        new Table({
          width: { size: 100, type: WidthType.PERCENTAGE },
          rows
        })
      );
      children.push(new Paragraph({ spacing: { after: 120 } }));
    }
  }

  return new Document({
    sections: [
      {
        properties: {},
        headers: {
          default: new Header({
            children: [
              new Paragraph({
                alignment: AlignmentType.RIGHT,
                children: [
                  new TextRun({
                    text: 'Microsoft Enterprise Quality Architecture  |  Thomas S. Snyder',
                    size: 16,
                    font: 'Segoe UI',
                    color: '94a3b8'
                  })
                ]
              })
            ]
          })
        },
        footers: {
          default: new Footer({
            children: [
              new Paragraph({
                alignment: AlignmentType.RIGHT,
                children: [
                  new TextRun({
                    text: 'Page ',
                    size: 16,
                    font: 'Segoe UI',
                    color: '94a3b8'
                  }),
                  new TextRun({
                    children: [PageNumber.CURRENT],
                    size: 16,
                    font: 'Segoe UI',
                    color: '94a3b8'
                  }),
                  new TextRun({
                    text: ' of ',
                    size: 16,
                    font: 'Segoe UI',
                    color: '94a3b8'
                  }),
                  new TextRun({
                    children: [PageNumber.TOTAL_PAGES],
                    size: 16,
                    font: 'Segoe UI',
                    color: '94a3b8'
                  })
                ]
              })
            ]
          })
        },
        children
      }
    ]
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// BUILD EXECUTION
// ─────────────────────────────────────────────────────────────────────────────

async function main() {
  console.log('🚀 Compiling Microsoft Quality Leadership Dossier across Markdown, DOCX, and PDF...\n');

  const files = [
    {
      baseName: '01_Cross_Quadrant_Telemetry_Blueprint',
      title: 'Cross-Quadrant Telemetry & Observability Blueprint',
      mdContent: DOC_1_MD,
      sections: [
        {
          h1: '1. Executive Summary & Problem Formulation',
          quote: 'Infrastructure teams monitor hypervisors; network engineers monitor switch fabrics; microservice teams track gRPC error rates; product teams track SaaS p99 latency. Because these streams are siloed, systemic degradations manifest as ghost failures.',
          p: [
            'In high-scale distributed cloud platforms, traditional monitoring suffers from the Siloed Observability Fallacy. Subtle degradations in silicon or OS kernels ripple upward into delayed, catastrophic application outages.',
            'This blueprint establishes a Cross-Quadrant Telemetry & Observability Plane correlating signals from bare-metal silicon and OS kernels directly to SaaS customer-journey metrics, enabling automated failure deflection 30 to 120 seconds before customer SLO breach.'
          ]
        },
        {
          h1: '2. The Four Observability Quadrants',
          table: {
            headers: ['Quadrant', 'Telemetry Focus', 'Key Signals', 'Capture Seams'],
            rows: [
              ['Q1: Silicon & Hardware', 'Bare-metal physical health', 'PCIe CRC errors, NIC ring drops, thermal throttling, NVMe queue depth', 'IPMI, BMC, WTT/HLK hardware lab tools'],
              ['Q2: OS Kernel & Runtime', 'System execution & sockets', 'Windows ETW, Linux eBPF, TCP RTO, cgroup limits, WinDbg dumps', 'WinDbg symbol dumps, eBPF daemonsets, OS perf counters'],
              ['Q3: Microservices Mesh', 'Distributed transport & queues', 'W3C traces, gRPC status codes, Envoy latency, Kafka lag', 'OpenTelemetry SDK, Envoy sidecars, Karate BDD probes'],
              ['Q4: SaaS Experience', 'Customer-facing journeys', 'RUM metrics, synthetic user journeys, DOM stalls (>50ms)', 'Playwright headless probes, BrowserStack nodes, RUM client tokens']
            ]
          }
        },
        {
          h1: '3. Cross-Quadrant Telemetry Correlation Architecture',
          p: [
            'Every inbound request receives an immutable W3C traceparent header. As the request descends through the topology, proxies bind physical node IDs, container cgroups, and OS thread IDs to the trace.',
            'Temporal Lag Heuristics: Hardware anomalies (Q1) precede kernel socket backlogs (Q2) by 15s, microservice queue stalls (Q3) by 45s, and user-facing SaaS latency breaches (Q4) by 75s. Early detection triggers automatic mitigation before customer SLOs are breached.'
          ]
        },
        {
          h1: '4. Preemptive Failure Detection & Automated Mitigation Engine',
          table: {
            headers: ['Severity Level', 'Lead Indicator (Q1/Q2)', 'Lag Indicator (Q3/Q4)', 'Automated Mitigation Action'],
            rows: [
              ['Tier 1: Minor Degrade', 'Node CPU thermal throttle >15% or NIC drop spike', 'API p95 latency elevates <10%', 'Soft traffic bleed: stop scheduling new pods on node; shift non-critical background jobs.'],
              ['Tier 2: Host Saturation', 'Kernel socket buffer allocation >85%', 'Microservice connection queue depth doubling', 'Canary drain: cordon node; graceful 15s SIGTERM pod eviction.'],
              ['Tier 3: Systemic Core Failure', 'PCIe bus fatal errors or uncorrectable panic', 'Downstream API p99 latency breaches 1,500ms', 'Hard circuit trip: failover regional ingress; trigger WinDbg dump analysis.']
            ]
          }
        },
        {
          h1: '5. Implementation Roadmap & QA Governance',
          bullets: [
            'Sprint 1–3: Standardize OpenTelemetry collectors; deploy eBPF kernel telemetry daemonsets across cluster nodes.',
            'Sprint 4–6: Deploy unified trace tagging linking pod identifiers to host hardware metrics in Azure Monitor / Splunk.',
            'Sprint 7–9: Validate automated canary drain policies using automated chaos injection; certify zero 5xx leakage.',
            'Sprint 10+: Integrate telemetry-driven quality gates directly into Azure DevOps CI/CD pipelines to block builds showing abnormal syscall distributions.'
          ]
        }
      ]
    },
    {
      baseName: '02_Chaos_Injection_Matrix_Fault_Tolerance_Spec',
      title: 'CI/CD Chaos Injection Matrix & Fault-Tolerance Specification',
      mdContent: DOC_2_MD,
      sections: [
        {
          h1: '1. Specification Scope & Engineering Doctrine',
          quote: '"Garbage In, Garbage Out" is not an aphorism—it is an active testing doctrine. A resilient system rejects garbage at the boundary, degrades gracefully, and maintains unbroken uptime for unaffected workloads.',
          p: [
            'This specification details the CI/CD Chaos Injection Matrix: an automated testing framework integrated into staging and release pipelines that systematically attacks microservice boundaries with malicious, malformed, and hostile stimuli.'
          ]
        },
        {
          h1: '2. The 5-Vector Automated Chaos Matrix',
          table: {
            headers: ['Vector', 'Injected Fault Scenario', 'Boundary Under Test', 'Expected Degradation', 'Automated Pass/Fail Gate'],
            rows: [
              ['Vector 1: Malformed Payloads ("Garbage In")', 'Truncated JSON, integer overflows (-1, 2^63-1), null bytes, schema drift', 'API Gateway, Ingestion Deserializers', 'Immediate HTTP 400/422; structured RFC-7807 error; zero process crashes', '100% rejection rate; zero pod restarts; memory delta <= 2%'],
              ['Vector 2: Network Degradation & Jitter', 'Injected latency (200-2500ms), 10-30% packet loss, TLS renegotiation stall', 'Inter-service transport, Envoy proxy mesh', 'Client timeouts enforced at 1200ms; cached fallback; exponential backoff', 'Zero connection pool starvation; circuit breakers report Healthy or Half-Open'],
              ['Vector 3: Dependency Death & Blackholing', 'Upstream Auth or DB primary drops to 0% availability (dropped SYN, 503)', 'Ingress Gateway, Service Mesh Circuit Breaker', 'Circuit breaker trips to Open after 3 failed probes; service serves cached data', 'Downstream services maintain >= 99.9% availability; failover <= 2.0s'],
              ['Vector 4: Ephemeral Resource Starvation', 'CPU throttle (100% busy spin), memory ballooning, disk IOPS saturation', 'Kubernetes Kubelet, Pod Scheduler', 'Readiness probe fails, removing pod from rotation; pod recycles cleanly', 'Zero 5xx errors served to end users; HPA scales new replica in <= 45s'],
              ['Vector 5: Token & Security Entropy', 'Expired JWTs, signature tampering, cross-tenant ID injection, replay nonce reuse', 'OAuth2/OIDC Middleware, API Gateway', 'Immediate HTTP 401/403 rejection at outer perimeter; security audit logged', 'Zero internal compute cycles wasted; zero sensitive trace leakage in response']
            ]
          }
        },
        {
          h1: '3. Detailed Fault Injection Methodology',
          bullets: [
            'Vector 1 Ingestion Fuzzing: Injects numeric boundaries (0, -1, 2^63-1, NaN), 1MB string buffers, and deeply nested JSON (>100 levels) to verify zero unhandled null pointer or stack overflow panics.',
            'Vector 2 MitM & Proxy Degradation: Ephemeral proxy sidecars inject artificial TCP window shrinkage and packet duplication to verify clean socket recycling upon hitting 1,200ms deadlines.',
            'Vector 3 Bulkhead Isolation: Synthetic black hole services accept TCP connections but never send ACKs; assertions guarantee bulkhead thread pools remain isolated and unaffected routes respond under 15ms.'
          ]
        },
        {
          h1: '4. CI/CD Pipeline Integration & Blast Radius Containment',
          p: [
            'Synthetic Isolation: Chaos injection runs exclusively against dedicated synthetic tenant accounts (tenant_id: synthetic_chaos_*). Shared database rows and cache keys are strictly namespace-isolated.',
            'Automated Abort Tripwires: If non-synthetic tenant traffic experiences any elevated latency or if the overall staging error rate exceeds 1.0%, the test harness triggers an immediate SIGKILL on chaos agents and restores baseline routing.',
            'Release Gate Artifact: Every CI/CD run generates an auditable Resiliency Attestation Certificate, confirming that the build withstood all 5 chaos vectors without human intervention.'
          ]
        }
      ]
    },
    {
      baseName: '03_Senior_Technical_Competency_Portfolio',
      title: 'Senior Technical Competency & Adaptability Portfolio',
      mdContent: DOC_3_MD,
      sections: [
        {
          h1: '1. Executive Perspective: Field-Tested Mastery vs Traditional Certifications',
          quote: 'While theoretical certifications establish shared vocabulary, enterprise cloud engineering demands rapid pattern recognition, ruthless triage, and the proven ability to turn legacy test debt into automated business ROI.',
          p: [
            'Over a 26-year career spanning 5 tenures at Microsoft, enterprise SaaS leaders like Smartsheet, high-throughput telecom microservices at OpenMarket, and console hardware ecosystems at Xbox, true quality leadership has always been defined by ruthless pragmatism, zero-baseline velocity, and deep diagnostic curiosity.'
          ]
        },
        {
          h1: '2. The 30-60-90 Day Rapid Assimilation Framework',
          table: {
            headers: ['Phase', 'Focus Area', 'Key Execution Objectives', 'Deliverable Outcome'],
            rows: [
              ['Days 1–30', 'Diagnostic Audit & "Rabbit" Exploration', 'Audit existing test suites (Signal vs Flake vs Dead Weight); map unwritten seams with Dev/Support; pioneer exploit-driven "Rabbit" speedrun passes', 'Quarantined non-blocking CI gate; prioritized technical debt backlog; unwritten failure mode map'],
              ['Days 31–60', 'High-ROI Automation Strike', 'Deploy zero-friction Karate/Playwright automation harness; automate top 15% core revenue paths (the 80/20 rule); embed Clean Slate quality gates in CI/CD', '0% to 85% automated regression coverage on critical paths; zero-flakiness PR gate; developers unblocked'],
              ['Days 61–90', 'Practice Elevation & Cultural Scale', 'Publish copy-pasteable test templates for developers; mentor junior/mid engineers; establish executive Quality KPIs (MTTD, DER, Flake Ratio)', 'Standardized cross-team QA practice; self-service developer testing; measurable drop in defect escapes']
            ]
          }
        },
        {
          h1: '3. Verified Field Case Studies & Historical Proof Points',
          bullets: [
            'Smartsheet (Zero-to-85% Karate Automation): Built Karate test suites from zero baseline to cover 85% of manual testing with 1,500 tests. Automated visual UI and performance coverage, freeing QA bandwidth for advanced exploratory testing.',
            'OpenMarket (Cloud Microservices Migration): Standardized QA for high-volume SMS/MMS/RCS microservices moving to AWS. Created reusable Karate API test templates and rewritten codebase documentation to accelerate company-wide cloud adoption.',
            'Microsoft Windows OS & Xbox (Hardware Scale & "Rabbit" Role): Developed WTT automated test beds and PXE network imaging infrastructure; performed white-box WinDbg stack trace crash analysis. At Xbox, pioneered the dedicated "Rabbit" speedrun completion testing role, scaling TCR testing throughput from 2-4 games/day to 8-16 games/day.'
          ]
        }
      ]
    }
  ];

  for (const item of files) {
    console.log(`\n📄 Processing: ${item.title}`);

    // 1. Write Markdown (.md)
    const mdPath = resolve(OUT_DIR, `${item.baseName}.md`);
    writeFileSync(mdPath, item.mdContent, 'utf8');
    console.log(`   ✅ Markdown: tailored_outputs/Microsoft_Principal_QA_Architect/${item.baseName}.md`);

    // 2. Write Word Document (.docx)
    const docxPath = resolve(OUT_DIR, `${item.baseName}.docx`);
    const docxDoc = createDocxDocument(item.title, item.sections);
    const docxBuffer = await Packer.toBuffer(docxDoc);
    writeFileSync(docxPath, docxBuffer);
    console.log(`   ✅ Word DOCX: tailored_outputs/Microsoft_Principal_QA_Architect/${item.baseName}.docx`);

    // 3. Write PDF (.pdf)
    const pdfPath = resolve(OUT_DIR, `${item.baseName}.pdf`);
    const bodyHtml = marked.parse(item.mdContent);
    const fullHtml = getHtmlWrapper(item.title, bodyHtml);
    await renderPdf(fullHtml, pdfPath);
    console.log(`   ✅ Print PDF:  tailored_outputs/Microsoft_Principal_QA_Architect/${item.baseName}.pdf`);
  }

  console.log('\n🎉 All 3 Microsoft deliverables successfully built in Markdown, DOCX, and PDF formats!');
}

main().catch((err) => {
  console.error('❌ Build failed:', err);
  process.exit(1);
});
