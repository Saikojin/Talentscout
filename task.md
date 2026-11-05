# Task Checklist: Crawler Failure Prevention & Anti-Block Resilience

## Intent Understanding
> **Core Objective:** Implement a comprehensive anti-block resilience suite across TalentScout's scouring pipeline to eliminate the 1,297 failures observed in production logs: introducing a zero-dependency Playwright stealth provider to bypass silent JS/CAPTCHA challenges (ZipRecruiter/Indeed 403s), a per-domain throttle and circuit breaker engine to prevent burst and cumulative rate-limiting (LinkedIn 429s), and an automated DNS quarantine utility to clean up dead domain endpoints (714 unreachable failures).

---

## Task DAG & Verification Contracts

- [x] **Task 1: Stealth Browser Context & Challenge Resolver (`scripts/browser_stealth.py`, `scripts/test_browser_stealth.py`)**
  - [GATE: QA]
  - Priority: 0
  - Dependencies: None
  - Design pure `scripts/browser_stealth.py`:
    - `create_stealth_context(browser, user_agent=None) -> BrowserContext`:
      - Masks `navigator.webdriver = undefined`.
      - Mocks realistic `navigator.plugins`, `navigator.languages`, and `window.chrome` runtime objects.
      - Sets authentic modern Windows Chrome headers (`Sec-Ch-Ua`, `Sec-Ch-Ua-Mobile`, `Sec-Ch-Ua-Platform`, `Accept-Language`).
      - Sets authentic 1920x1080 viewport and America/Los_Angeles timezone.
    - `resolve_transient_challenge(page, timeout_seconds=5) -> bool`:
      - Detects initial Cloudflare/Turnstile/CAPTCHA challenges.
      - Waits 3–5 seconds for the challenge token to self-resolve and redirect before declaring the page blocked.
  - **Verification command:** `python -m unittest scripts/test_browser_stealth.py` (7/7 passing)

- [x] **Task 2: Per-Domain Throttle & Circuit Breaker Engine (`scripts/rate_limiter.py`, `scripts/test_rate_limiter.py`)**
  - [GATE: QA]
  - Priority: 0
  - Dependencies: None
  - Design `scripts/rate_limiter.py`:
    - `DomainThrottle` class:
      - Per-domain concurrency limits (e.g., `linkedin.com`: max 1 concurrent tab; `indeed.com`: max 1; `glassdoor.com`: max 1; others: max 3).
      - Randomized inter-request delay jitter (e.g., 2.5s–4.0s for sensitive domains, 0.5s–1.0s for others).
      - `acquire(url) -> bool` and `release(url)`: non-blocking acquisition that respects cooldowns.
      - `trip_circuit_breaker(url, reason, cooldown_seconds=300)`: activates domain penalty box on HTTP 429.
      - `is_in_cooldown(url) -> tuple[bool, float, str]`: checks remaining cooldown seconds.
  - **Verification command:** `python -m unittest scripts/test_rate_limiter.py` (6/6 passing)

- [x] **Task 3: Integrate Stealth & Rate Throttling into Scour Loop (`scripts/auto_scour.py`, `scripts/test_scour_stealth_throttle.py`)**
  - [GATE: QA]
  - Priority: 1
  - Dependencies: Task 1, Task 2
  - In `auto_scour.py`:
    - Initialize browser with `create_stealth_context()` instead of bare context.
    - Instantiate shared `DomainThrottle` in `main()` and pass to `scrape_site`, `scrape_company`, and `fetch_job_description`.
    - In `scrape_site`:
      - Check `throttle.is_in_cooldown(url)`: if in cooldown, skip immediately and record telemetry without firing network request.
      - Acquire domain lock via `await throttle.acquire(url)` before navigation; release in `finally:`.
      - On challenge signature, attempt `await resolve_transient_challenge(page)`.
      - On HTTP 429 or repeated 403, call `throttle.trip_circuit_breaker(url, "HTTP 429 Rate Limited", cooldown=300)`.
    - In Phase 2 `worker()`:
      - Ensure JD fetching respects domain throttle and immediately bypasses jobs whose domain is in active cooldown.
  - **Verification command:** `python -m unittest scripts/test_scour_stealth_throttle.py` (3/3 passing)

- [x] **Task 4: DNS / Dead Domain Auto-Quarantine & Pruning Utility (`scripts/verify_site_health.py`, `scripts/test_site_health.py`)**
  - [GATE: QA]
  - Priority: 1
  - Dependencies: None
  - Design `scripts/verify_site_health.py`:
    - Sweeps all search configs, company career URLs, and ATS URLs in `job_tracker.db`, `job_search_sites.json`, and `base_companies.json`.
    - Non-blocking DNS and HTTP probe with 5-second timeout.
    - Automatically flags or prunes dead domains (resolving the 714 `DNS / Unreachable` errors).
    - Writes unreachable domains to `quarantined_domains.json` with timestamp and failure reason.
    - CLI options: `--audit-only`, `--prune-dead-domains`, `--timeout 5`.
  - **Verification command:** `python -m unittest scripts/test_site_health.py` (4/4 passing)

- [x] **Task 5: End-to-End Validation & Living Documentation Update (`CONTEXT.md`, `README.md`, full test sweep)**
  - [GATE: QA]
  - Priority: 2
  - Dependencies: Task 3, Task 4
  - Execute full test suite (`python -m unittest discover -s scripts -p "test_*.py"`).
  - Verify zero unhandled exceptions and 100% pass rate.
  - Update `README.md` and `CONTEXT.md` with stealth context details, domain rate limiter rules, and site health CLI usage.
  - **Verification command:** `python -m unittest discover -s scripts -p "test_*.py"` (60/60 passing)

---

## Seikojin QA Gatekeeping Checklist
- [x] 100% test pass rate across all new unit/integration tests with `python -m unittest`.
- [x] No regression on existing 40 unit and integration tests (60 total tests passing).
- [x] Zero unhandled Playwright navigation exceptions on challenged or throttled sites.
- [x] LinkedIn requests adhere to 1-tab concurrency and 2.5s+ jitter delay.
- [x] Circuit breaker trips cleanly on 429 without crashing worker queues.
- [x] `logs/scour_summary_latest.json` accurately reflects circuit breaker skips and challenge resolution stats.
