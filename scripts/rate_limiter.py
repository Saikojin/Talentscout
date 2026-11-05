import asyncio
import random
import time
from contextlib import asynccontextmanager
from typing import Dict, Optional, Tuple, Any
from urllib.parse import urlparse

# Pre-defined rate limiting & concurrency policies for sensitive job platforms
DEFAULT_POLICIES: Dict[str, Dict[str, Any]] = {
    "linkedin.com": {
        "max_concurrency": 1,
        "min_delay": 2.5,
        "max_delay": 4.0,
        "cooldown": 300,  # 5 minutes
    },
    "indeed.com": {
        "max_concurrency": 1,
        "min_delay": 2.0,
        "max_delay": 3.5,
        "cooldown": 300,
    },
    "glassdoor.com": {
        "max_concurrency": 1,
        "min_delay": 2.0,
        "max_delay": 3.5,
        "cooldown": 300,
    },
    "ziprecruiter.com": {
        "max_concurrency": 1,
        "min_delay": 2.0,
        "max_delay": 3.0,
        "cooldown": 300,
    },
    "DEFAULT": {
        "max_concurrency": 3,
        "min_delay": 0.5,
        "max_delay": 1.0,
        "cooldown": 60,
    },
}

KNOWN_SITE_DOMAINS: Dict[str, str] = {
    "linkedin": "linkedin.com",
    "indeed": "indeed.com",
    "glassdoor": "glassdoor.com",
    "ziprecruiter": "ziprecruiter.com",
    "builtin": "builtin.com",
    "dice": "dice.com",
    "simplyhired": "simplyhired.com",
    "careerbuilder": "careerbuilder.com",
    "monster": "monster.com",
    "hiring cafe": "hiring.cafe",
    "outscal": "outscal.com",
    "techfetch": "techfetch.com",
}

def normalize_domain(target: str) -> str:
    """Extract and normalize the root domain from a URL or site name."""
    if not target:
        return "unknown"

    target_clean = target.strip()
    lowered = target_clean.lower()

    if lowered in KNOWN_SITE_DOMAINS:
        return KNOWN_SITE_DOMAINS[lowered]

    if "://" in target_clean or target_clean.startswith("//"):
        host = urlparse(target_clean).netloc.lower()
    else:
        host = target_clean.lower().split("/")[0]

    # Strip port if present
    if ":" in host:
        host = host.split(":")[0]

    # Normalize subdomains to root domain for known services
    if host.endswith("linkedin.com"):
        return "linkedin.com"
    if host.endswith("indeed.com"):
        return "indeed.com"
    if host.endswith("glassdoor.com"):
        return "glassdoor.com"
    if host.endswith("ziprecruiter.com"):
        return "ziprecruiter.com"

    # Remove www.
    if host.startswith("www."):
        host = host[4:]

    return host or "unknown"


class DomainThrottle:
    """
    Coordinates per-domain request rate-limiting, concurrency locks,
    jitter intervals, and HTTP 429 cooldown circuit breakers.
    """
    def __init__(self, custom_policies: Optional[Dict[str, Dict[str, Any]]] = None):
        self.policies = dict(DEFAULT_POLICIES)
        if custom_policies:
            self.policies.update(custom_policies)

        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._last_request_time: Dict[str, float] = {}
        self._circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self._skipped_counts: Dict[str, int] = {}
        self._lock = asyncio.Lock()

    def get_policy(self, domain: str) -> Dict[str, Any]:
        """Fetch policy for domain, falling back to DEFAULT."""
        return self.policies.get(domain, self.policies["DEFAULT"])

    def _get_semaphore(self, domain: str) -> asyncio.Semaphore:
        """Get or create the asyncio Semaphore for a given domain."""
        if domain not in self._semaphores:
            policy = self.get_policy(domain)
            max_c = policy.get("max_concurrency", 3)
            self._semaphores[domain] = asyncio.Semaphore(max_c)
        return self._semaphores[domain]

    def is_in_cooldown(self, target: str) -> Tuple[bool, float, str]:
        """
        Check if a domain is currently under a circuit breaker cooldown.
        Returns: (is_in_cooldown, remaining_seconds, reason)
        """
        domain = normalize_domain(target)
        cb = self._circuit_breakers.get(domain)
        if not cb:
            return False, 0.0, ""

        now = time.time()
        cooldown_until = cb.get("cooldown_until", 0.0)
        remaining = cooldown_until - now
        if remaining > 0:
            return True, remaining, cb.get("reason", "Domain under rate limit cooldown")

        # Cooldown expired: automatically clear circuit breaker
        del self._circuit_breakers[domain]
        return False, 0.0, ""

    def trip_circuit_breaker(self, target: str, reason: str = "Rate limited", cooldown_seconds: Optional[int] = None):
        """
        Trip the circuit breaker for a domain, placing it in a temporary penalty box.
        """
        domain = normalize_domain(target)
        policy = self.get_policy(domain)
        duration = cooldown_seconds if cooldown_seconds is not None else policy.get("cooldown", 300)
        cooldown_until = time.time() + duration

        self._circuit_breakers[domain] = {
            "cooldown_until": cooldown_until,
            "reason": reason,
            "duration": duration,
            "tripped_at": time.time()
        }
        print(f"[!] [THROTTLE] Circuit breaker TRIPPED for {domain} ({reason}). Cooldown: {duration}s")

    async def acquire(self, target: str) -> bool:
        """
        Acquire permission to make a request to the target domain.
        Returns True if acquired, or False if bypassed due to active circuit breaker.
        Enforces per-domain concurrency and inter-request jitter delay.
        """
        domain = normalize_domain(target)
        in_cb, remaining, reason = self.is_in_cooldown(domain)
        if in_cb:
            self._skipped_counts[domain] = self._skipped_counts.get(domain, 0) + 1
            return False

        sem = self._get_semaphore(domain)
        await sem.acquire()

        # Enforce inter-request jitter delay
        policy = self.get_policy(domain)
        min_d = policy.get("min_delay", 0.5)
        max_d = policy.get("max_delay", 1.0)
        target_delay = random.uniform(min_d, max_d)

        now = time.time()
        last_req = self._last_request_time.get(domain, 0.0)
        elapsed = now - last_req

        if elapsed < target_delay:
            wait_time = target_delay - elapsed
            await asyncio.sleep(wait_time)

        self._last_request_time[domain] = time.time()
        return True

    def release(self, target: str):
        """Release the concurrency lock for the domain."""
        domain = normalize_domain(target)
        sem = self._semaphores.get(domain)
        if sem:
            sem.release()

    @asynccontextmanager
    async def guard(self, target: str):
        """Async context manager for acquiring and safely releasing domain throttle."""
        acquired = await self.acquire(target)
        if not acquired:
            yield False
            return
        try:
            yield True
        finally:
            self.release(target)

    def get_metrics(self) -> Dict[str, Any]:
        """Return rate limiter state and telemetry metrics."""
        now = time.time()
        active_cooldowns = {}
        for dom, cb in list(self._circuit_breakers.items()):
            remaining = cb["cooldown_until"] - now
            if remaining > 0:
                active_cooldowns[dom] = {
                    "remaining_seconds": round(remaining, 1),
                    "reason": cb["reason"]
                }
            else:
                del self._circuit_breakers[dom]

        return {
            "active_cooldowns": active_cooldowns,
            "skipped_counts": dict(self._skipped_counts),
        }
