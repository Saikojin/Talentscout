import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from scripts.rate_limiter import DomainThrottle
from scripts.scour_telemetry import ScourTelemetry
from scripts.auto_scour import scrape_site, process_discovered_job

class TestScourStealthThrottle(unittest.TestCase):
    def setUp(self):
        self.telemetry = ScourTelemetry()
        self.throttle = DomainThrottle({
            "testsite.com": {"max_concurrency": 1, "min_delay": 0.01, "max_delay": 0.02, "cooldown": 5}
        })
        self.semaphore = asyncio.Semaphore(5)

    def test_scrape_site_skips_when_domain_in_cooldown(self):
        async def run_test():
            self.throttle.trip_circuit_breaker("https://testsite.com/jobs", "HTTP 429", cooldown_seconds=60)

            mock_context = MagicMock()
            mock_page = AsyncMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)

            config = {
                "site_name": "TestSite",
                "search_url": "https://testsite.com/search?q={search_term}",
                "job_card_selector": ".card"
            }

            jobs = await scrape_site(
                mock_context, "TestSite", config, config, "QA", "Seattle",
                self.semaphore, telemetry=self.telemetry, throttle=self.throttle
            )

            self.assertEqual(len(jobs), 0)
            mock_page.goto.assert_not_called()
            # Should have recorded a cooldown bypass in telemetry
            self.assertTrue(any("Cooldown Bypassed" in b["block_type"] for b in self.telemetry.blocks))

        asyncio.run(run_test())

    def test_scrape_site_trips_circuit_breaker_on_429(self):
        async def run_test():
            mock_context = MagicMock()
            mock_page = AsyncMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)

            mock_response = MagicMock()
            mock_response.status = 429
            mock_page.goto = AsyncMock(return_value=mock_response)

            config = {
                "site_name": "TestSite",
                "search_url": "https://testsite.com/search?q={search_term}",
                "job_card_selector": ".card"
            }

            jobs = await scrape_site(
                mock_context, "TestSite", config, config, "QA", "Seattle",
                self.semaphore, telemetry=self.telemetry, throttle=self.throttle
            )

            self.assertEqual(len(jobs), 0)
            in_cd, _, _ = self.throttle.is_in_cooldown("https://testsite.com/search")
            self.assertTrue(in_cd)

        asyncio.run(run_test())

    def test_process_discovered_job_skips_in_cooldown(self):
        async def run_test():
            job_url = "https://testsite.com/job/999"
            self.throttle.trip_circuit_breaker(job_url, "Rate limit", cooldown_seconds=60)

            mock_context = MagicMock()
            job = {
                "title": "SDET",
                "company": "Test Co",
                "url": job_url,
                "site": "TestSite"
            }
            processed = set()

            res = await process_discovered_job(
                mock_context, job, self.semaphore, processed,
                telemetry=self.telemetry, throttle=self.throttle
            )

            self.assertIsNone(res)
            self.assertTrue(any("Cooldown Bypassed" in b["block_type"] for b in self.telemetry.blocks))

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
