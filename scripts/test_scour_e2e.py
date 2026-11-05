import unittest
import asyncio
import os
import json
import tempfile
from unittest.mock import MagicMock, AsyncMock, patch

from scripts.scour_telemetry import ScourTelemetry
from scripts.auto_scour import scrape_site, process_discovered_job
from scripts.pagination_utils import build_page_url, extract_page_count

class TestScourE2E(unittest.TestCase):
    def setUp(self):
        self.telemetry = ScourTelemetry()
        self.semaphore = asyncio.Semaphore(5)

    def test_scrape_site_detects_http_403_block(self):
        async def run_test():
            mock_context = MagicMock()
            mock_page = AsyncMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)

            mock_response = MagicMock()
            mock_response.status = 403
            mock_page.goto = AsyncMock(return_value=mock_response)

            config = {
                "site_name": "TestSite",
                "search_url": "https://example.com/search?q={search_term}&l={location}",
                "job_card_selector": ".card"
            }

            jobs = await scrape_site(
                mock_context, "TestSite", config, config, "QA", "Seattle",
                self.semaphore, telemetry=self.telemetry
            )
            self.assertEqual(len(jobs), 0)
            self.assertTrue(self.telemetry.has_blocks())
            self.assertEqual(self.telemetry.blocks[0]["block_type"], "HTTP 403 Forbidden")
            self.assertEqual(self.telemetry.blocks[0]["site"], "TestSite")

        asyncio.run(run_test())

    def test_scrape_site_detects_cloudflare_challenge(self):
        async def run_test():
            mock_context = MagicMock()
            mock_page = AsyncMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)

            mock_response = MagicMock()
            mock_response.status = 200
            mock_page.goto = AsyncMock(return_value=mock_response)
            mock_page.title = AsyncMock(return_value="Just a moment...")
            mock_page.evaluate = AsyncMock(return_value="Checking your browser. Cloudflare Ray ID: abc123")
            mock_page.url = "https://example.com/cf-check"

            config = {
                "site_name": "CloudflareSite",
                "search_url": "https://example.com/search?q={search_term}&l={location}",
                "job_card_selector": ".card"
            }

            jobs = await scrape_site(
                mock_context, "CloudflareSite", config, config, "QA", "Seattle",
                self.semaphore, telemetry=self.telemetry
            )
            self.assertEqual(len(jobs), 0)
            self.assertTrue(self.telemetry.has_blocks())
            self.assertEqual(self.telemetry.blocks[0]["block_type"], "Cloudflare Challenge")

        asyncio.run(run_test())

    def test_scrape_site_detect_pages_only(self):
        async def run_test():
            mock_context = MagicMock()
            mock_page = AsyncMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)

            mock_response = MagicMock()
            mock_response.status = 200
            mock_page.goto = AsyncMock(return_value=mock_response)
            mock_page.title = AsyncMock(return_value="QA Jobs")
            mock_page.evaluate = AsyncMock(return_value="Showing 1 to 25 of 150 jobs. Page 1 of 6.")
            mock_page.url = "https://example.com/jobs"

            config = {
                "site_name": "BuiltInTest",
                "search_url": "https://example.com/jobs?q={search_term}",
                "pagination_type": "page_param",
                "page_param": "page",
                "items_per_page": 25,
                "job_card_selector": ".card"
            }

            jobs = await scrape_site(
                mock_context, "BuiltInTest", config, config, "QA", "Seattle",
                self.semaphore, telemetry=self.telemetry, detect_pages_only=True
            )
            # Should exit early without returning jobs
            self.assertEqual(len(jobs), 0)
            # Should have recorded page capacity
            self.assertIn("BuiltInTest", self.telemetry.page_counts)
            self.assertEqual(self.telemetry.page_counts["BuiltInTest"]["page_count"], 6)

        asyncio.run(run_test())

    def test_scrape_site_target_page_url_construction(self):
        async def run_test():
            mock_context = MagicMock()
            mock_page = AsyncMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)

            visited_urls = []
            async def fake_goto(url, **kwargs):
                visited_urls.append(url)
                mock_resp = MagicMock()
                mock_resp.status = 200
                return mock_resp

            mock_page.goto = fake_goto
            mock_page.title = AsyncMock(return_value="QA Jobs Page 2")
            mock_page.evaluate = AsyncMock(return_value="Jobs content")
            mock_page.url = "https://example.com/jobs"
            mock_page.wait_for_selector = AsyncMock()
            mock_page.locator = MagicMock(return_value=MagicMock(all=AsyncMock(return_value=[])))

            config = {
                "site_name": "DiceTest",
                "search_url": "https://dice.com/jobs?q={search_term}&location={location}",
                "pagination_type": "page_param",
                "page_param": "page"
            }

            await scrape_site(
                mock_context, "DiceTest", config, config, "SDET", "Seattle",
                self.semaphore, telemetry=self.telemetry, target_page=3
            )
            self.assertTrue(any("page=3" in u for u in visited_urls))

        asyncio.run(run_test())

    def test_process_discovered_job_rejection_tracking(self):
        async def run_test():
            mock_context = MagicMock()
            job = {
                "title": "Software Tester",
                "company": "Offshore Corp",
                "url": "https://example.com/job/123",
                "site": "TestBoard",
                "description": "Location is in Lahore, Pakistan. Required Cobol programming."
            }

            processed_urls = set()
            with patch("scripts.auto_scour.is_duplicate", return_value=False):
                res = await process_discovered_job(
                    mock_context, job, self.semaphore, processed_urls,
                    telemetry=self.telemetry, dry_run=True
                )
                self.assertIsNotNone(res)
                self.assertTrue(res["filter_results"]["is_disqualified"])
                self.assertEqual(self.telemetry.total_rejections(), 1)
                rejection_stats = self.telemetry.get_rejection_stats()
                # Should be caught by Location / Foreign Country
                self.assertGreaterEqual(rejection_stats.get("Location / Foreign Country", 0), 1)

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
