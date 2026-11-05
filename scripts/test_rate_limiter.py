import unittest
import asyncio
import time
from scripts.rate_limiter import (
    DomainThrottle,
    normalize_domain,
    DEFAULT_POLICIES,
)

class TestRateLimiter(unittest.TestCase):
    def setUp(self):
        self.throttle = DomainThrottle()

    def test_normalize_domain(self):
        self.assertEqual(normalize_domain("https://www.linkedin.com/jobs/search?q=QA"), "linkedin.com")
        self.assertEqual(normalize_domain("https://ca.linkedin.com/jobs/view/123"), "linkedin.com")
        self.assertEqual(normalize_domain("https://indeed.com/jobs"), "indeed.com")
        self.assertEqual(normalize_domain("LinkedIn"), "linkedin.com")
        self.assertEqual(normalize_domain("Dice"), "dice.com")
        self.assertEqual(normalize_domain("https://example.org/careers"), "example.org")

    def test_default_policies_exist(self):
        self.assertIn("linkedin.com", DEFAULT_POLICIES)
        self.assertEqual(DEFAULT_POLICIES["linkedin.com"]["max_concurrency"], 1)
        self.assertGreaterEqual(DEFAULT_POLICIES["linkedin.com"]["min_delay"], 2.0)
        self.assertEqual(DEFAULT_POLICIES["linkedin.com"]["cooldown"], 300)

    def test_circuit_breaker_tripping_and_recovery(self):
        domain = "linkedin.com"
        in_cb, remaining, reason = self.throttle.is_in_cooldown(domain)
        self.assertFalse(in_cb)

        # Trip for 0.2 seconds
        self.throttle.trip_circuit_breaker(domain, reason="HTTP 429 Test", cooldown_seconds=0.2)
        in_cb, remaining, reason = self.throttle.is_in_cooldown(domain)
        self.assertTrue(in_cb)
        self.assertGreater(remaining, 0.0)
        self.assertEqual(reason, "HTTP 429 Test")

        # Sleep and verify recovery
        time.sleep(0.25)
        in_cb, remaining, reason = self.throttle.is_in_cooldown(domain)
        self.assertFalse(in_cb)
        self.assertEqual(remaining, 0.0)

    def test_acquire_skips_when_in_cooldown(self):
        async def run_test():
            domain = "https://www.linkedin.com/jobs"
            self.throttle.trip_circuit_breaker(domain, reason="HTTP 429", cooldown_seconds=60)
            
            acquired = await self.throttle.acquire(domain)
            self.assertFalse(acquired)
            self.assertEqual(self.throttle.get_metrics()["skipped_counts"]["linkedin.com"], 1)

        asyncio.run(run_test())

    def test_acquire_and_release_flow(self):
        async def run_test():
            # Use small custom policy for fast testing
            fast_policies = {
                "fast.com": {"max_concurrency": 1, "min_delay": 0.05, "max_delay": 0.1, "cooldown": 5}
            }
            throttle = DomainThrottle(custom_policies=fast_policies)
            domain = "https://fast.com/jobs"

            t0 = time.time()
            acq1 = await throttle.acquire(domain)
            self.assertTrue(acq1)
            throttle.release(domain)

            acq2 = await throttle.acquire(domain)
            self.assertTrue(acq2)
            throttle.release(domain)
            t1 = time.time()

            # Second acquire should have respected the min_delay
            self.assertGreaterEqual(t1 - t0, 0.05)

        asyncio.run(run_test())

    def test_guard_context_manager(self):
        async def run_test():
            fast_policies = {
                "test.com": {"max_concurrency": 1, "min_delay": 0.01, "max_delay": 0.02, "cooldown": 5}
            }
            throttle = DomainThrottle(custom_policies=fast_policies)
            
            executed = False
            async with throttle.guard("https://test.com/careers") as allowed:
                self.assertTrue(allowed)
                executed = True

            self.assertTrue(executed)

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
