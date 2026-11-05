import datetime
import json
import os
import re
from typing import Dict, List, Optional, Any

HTTP_BLOCK_CODES = {
    403: "HTTP 403 Forbidden",
    429: "HTTP 429 Rate Limited",
    503: "HTTP 503 Service Unavailable",
}

CLOUDFLARE_SIGNATURES = [
    "just a moment...",
    "attention required! | cloudflare",
    "checking your browser before accessing",
    "cloudflare ray id",
]

TURNSTILE_SIGNATURES = [
    "cloudflare turnstile",
    "cf-turnstile",
    "verify you are human",
]

BOT_CHALLENGE_SIGNATURES = [
    "datadome",
    "perimeterx",
    "press & hold",
    "px-captcha",
    "hcaptcha",
    "recaptcha",
    "please verify you are a human",
    "access denied",
    "request blocked",
    "you don't have permission to access",
    "security check",
    "bot detection",
    "unusual traffic from your computer network",
]

def detect_http_block(status_code: int) -> Optional[str]:
    """Classify HTTP status codes that represent crawler blocks or rate limits."""
    return HTTP_BLOCK_CODES.get(status_code)

def detect_dom_challenge(title: str, body_text: str, current_url: str = "") -> Optional[str]:
    """
    Inspect the page title, DOM body text, and final URL to detect WAF challenges,
    CAPTCHAs, bot shields, or forced authentication redirects.
    """
    url_lower = (current_url or "").lower()
    title_lower = (title or "").lower()
    body_lower = (body_text or "").lower()

    # 1. URL-based Auth Walls
    if "linkedin.com" in url_lower and ("/login" in url_lower or "/checkpoint" in url_lower):
        return "LinkedIn Login Wall"
    if "glassdoor.com" in url_lower and ("/member" in url_lower or "/login" in url_lower):
        return "Glassdoor Auth Wall"
    if "indeed.com" in url_lower and ("/challenge" in url_lower or "/verify" in url_lower):
        return "Indeed Security Challenge"

    # 2. Cloudflare Turnstile & Verification
    if any(sig in title_lower or sig in body_lower for sig in TURNSTILE_SIGNATURES):
        return "Cloudflare Turnstile"

    # 3. Cloudflare Standard Waiting Rooms / Ray ID challenges
    if any(sig in title_lower or sig in body_lower for sig in CLOUDFLARE_SIGNATURES):
        return "Cloudflare Challenge"

    # 4. Other WAF / Bot Defense Signatures
    for sig in BOT_CHALLENGE_SIGNATURES:
        if sig in title_lower or (sig in body_lower and len(body_lower) < 2000):
            # Only trigger on body if page text is relatively sparse (typical challenge page)
            return f"Bot Shield Challenge ({sig.title()})"

    return None

class ScourTelemetry:
    """
    Central collector for crawler telemetry, block events, blacklist skips,
    rejection reasons, page depth discovery, and overall scour yield.
    """
    def __init__(self):
        self.start_time = datetime.datetime.now()
        self.blocks: List[Dict[str, Any]] = []
        self.blacklist_skips: List[Dict[str, str]] = []
        self.rejections: Dict[str, List[Dict[str, Any]]] = {
            "Location / Foreign Country": [],
            "Disqualified Skill": [],
            "Negative Title Keyword": [],
            "Empty JD SafetyNet": [],
            "Low Score": [],
            "Other": []
        }
        self.page_counts: Dict[str, Dict[str, Any]] = {}
        self.throttle_metrics: Dict[str, Any] = {}
        self.yield_stats = {
            "discovered": 0,
            "processed": 0,
            "passed": 0
        }

    def record_throttle_metrics(self, metrics: Dict[str, Any]):
        """Record domain throttle and circuit breaker state."""
        self.throttle_metrics = metrics or {}

    def record_block(self, site: str, url: str, block_type: str, details: str = ""):
        """Record a site or URL where the scraper was blocked or challenged."""
        self.blocks.append({
            "site": site,
            "url": url,
            "block_type": block_type,
            "details": details,
            "timestamp": datetime.datetime.now().isoformat()
        })

    def has_blocks(self) -> bool:
        return len(self.blocks) > 0

    def record_blacklist_skip(self, target: str, reason: str = "Domain/company blacklisted"):
        """Record a company or job board skipped due to blacklist matching."""
        self.blacklist_skips.append({
            "target": target,
            "reason": reason,
            "timestamp": datetime.datetime.now().isoformat()
        })

    def record_rejection(self, job_title: str, company: str, reasons: List[str]):
        """Categorize and record a disqualified job."""
        if not reasons:
            reasons = ["Unknown reason"]

        reasons_str = " ".join(reasons).lower()
        if any(w in reasons_str for w in ["country", "location", "foreign", "state", "restricted", "out of state"]):
            category = "Location / Foreign Country"
        elif "disqualified skill" in reasons_str:
            category = "Disqualified Skill"
        elif "negative title" in reasons_str or "title keyword" in reasons_str:
            category = "Negative Title Keyword"
        elif "empty or invalid" in reasons_str or "safetynet" in reasons_str:
            category = "Empty JD SafetyNet"
        elif "score" in reasons_str:
            category = "Low Score"
        else:
            category = "Other"

        self.rejections[category].append({
            "title": job_title,
            "company": company,
            "reasons": reasons
        })

    def get_rejection_stats(self) -> Dict[str, int]:
        """Return counts of rejections by category."""
        return {cat: len(items) for cat, items in self.rejections.items()}

    def total_rejections(self) -> int:
        return sum(len(items) for items in self.rejections.values())

    def record_page_count(self, site: str, page_count: int, total_jobs: Optional[int] = None):
        """Record the total pages and job volume discovered for a given site."""
        self.page_counts[site] = {
            "page_count": page_count,
            "total_jobs": total_jobs
        }

    def record_job_discovered(self, count: int = 1):
        self.yield_stats["discovered"] += count

    def record_job_processed(self, count: int = 1):
        self.yield_stats["processed"] += count

    def record_job_passed(self, count: int = 1):
        self.yield_stats["passed"] += count

    def format_summary(self) -> str:
        """Render a formatted, high-density ASCII summary table for terminal output."""
        elapsed = (datetime.datetime.now() - self.start_time).total_seconds()
        lines = [
            "",
            "=" * 70,
            f"                     SCOUR SUMMARY REPORT ({elapsed:.1f}s)",
            "=" * 70,
        ]

        # 1. Scour Yield Section
        disc = self.yield_stats["discovered"]
        proc = self.yield_stats["processed"]
        passed = self.yield_stats["passed"]
        pass_rate = (passed / proc * 100) if proc > 0 else 0.0

        lines.extend([
            f" [YIELD] Discovered: {disc} | Processed: {proc} | Passed: {passed} ({pass_rate:.1f}%)",
            "-" * 70
        ])

        # 2. Crawler Blocks Section
        if self.blocks:
            lines.append(f" [!] CRAWLER BLOCKS & BOT DEFENSES DETECTED ({len(self.blocks)} sites blocked):")
            for b in self.blocks:
                site = b['site']
                b_type = b['block_type']
                url = b['url']
                details = f" ({b['details']})" if b.get('details') else ""
                lines.append(f"     * {site:15} | {b_type}{details}")
                if url:
                    lines.append(f"       URL: {url}")
            lines.append("-" * 70)
        else:
            lines.append(" [+] Crawler Blocks: 0 detected (all active sites accessible)")
            lines.append("-" * 70)

        # 3. Blacklist Skips Section
        if self.blacklist_skips:
            targets = [s['target'] for s in self.blacklist_skips]
            sample = ", ".join(targets[:5]) + ("..." if len(targets) > 5 else "")
            lines.append(f" [*] Blacklist Skips: {len(self.blacklist_skips)} pre-filtered ({sample})")
            lines.append("-" * 70)

        # 4. Rejection Breakdown Section
        total_rej = self.total_rejections()
        lines.append(f" [REJECTIONS] Total Disqualified: {total_rej}")
        for cat, items in self.rejections.items():
            if items:
                lines.append(f"     - {cat:28}: {len(items):3d}")
                # Show up to 2 examples
                for sample in items[:2]:
                    r_str = "/".join(sample['reasons'][:2])
                    lines.append(f"         > {sample['title'][:32]} ({sample['company'][:18]}) -> {r_str}")
        lines.append("-" * 70)

        # 5. Page Depth & Pagination Discovered
        if self.page_counts:
            lines.append(" [PAGE CAPACITY] Discovered Page Depth:")
            for site, pinfo in self.page_counts.items():
                p_cnt = pinfo.get("page_count", 1)
                t_jobs = pinfo.get("total_jobs")
                jobs_str = f" (~{t_jobs} listings)" if t_jobs is not None else ""
                lines.append(f"     * {site:20}: {p_cnt} page(s) available{jobs_str}")
            lines.append("-" * 70)

        # 6. Throttle & Circuit Breaker Telemetry
        if self.throttle_metrics:
            cooldowns = self.throttle_metrics.get("active_cooldowns", {})
            skipped = self.throttle_metrics.get("skipped_counts", {})
            if cooldowns or skipped:
                lines.append(" [RATE THROTTLE & CIRCUIT BREAKERS]:")
                if cooldowns:
                    lines.append(f"     * Active Cooldowns ({len(cooldowns)} domains):")
                    for dom, cinfo in cooldowns.items():
                        lines.append(f"       - {dom:20}: {cinfo['remaining_seconds']}s remaining ({cinfo['reason']})")
                if skipped:
                    lines.append(f"     * Requests Bypassed During Cooldown:")
                    for dom, scnt in skipped.items():
                        lines.append(f"       - {dom:20}: {scnt} requests spared")
                lines.append("-" * 70)

        lines.append("=" * 70)
        return "\n".join(lines)

    def print_summary(self):
        print(self.format_summary())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize telemetry data to a dictionary."""
        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "duration_seconds": (datetime.datetime.now() - self.start_time).total_seconds(),
            "yield": self.yield_stats,
            "blocks": self.blocks,
            "blacklist_skips": self.blacklist_skips,
            "rejections": {
                cat: [
                    {"title": item["title"], "company": item["company"], "reasons": item["reasons"]}
                    for item in items
                ]
                for cat, items in self.rejections.items()
            },
            "rejection_counts": self.get_rejection_stats(),
            "page_counts": self.page_counts,
            "throttle_metrics": self.throttle_metrics
        }

    def save_json(self, filepath: str):
        """Save telemetry metrics to a JSON file atomically."""
        dir_name = os.path.dirname(os.path.abspath(filepath))
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

        temp_path = f"{filepath}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        os.replace(temp_path, filepath)
