import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from scripts.scour_telemetry import ScourTelemetry
from scripts.auto_scour import scrape_site, scrape_company

class TestScourSelectorDrift(unittest.IsolatedAsyncioTestCase):
    async def test_scrape_site_card_drift_rescued(self):
        telemetry = ScourTelemetry()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.close = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        # Mock navigation response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto = AsyncMock(return_value=mock_response)
        mock_page.title = AsyncMock(return_value="Careers at ModernTech")
        mock_page.evaluate = AsyncMock(return_value="Current Job Openings")
        mock_page.url = "https://example.com/search?q=QA"

        # Primary selector fails
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("Timeout"))

        # Fallback card
        mock_card = MagicMock()
        mock_card.text_content = AsyncMock(return_value="Senior QA Engineer Acme Seattle")
        mock_card.evaluate = AsyncMock(return_value="article")
        mock_card.locator = MagicMock()

        # Inside card locators
        def card_locator_side_effect(sel):
            loc = MagicMock()
            first = MagicMock()
            if "title" in sel or sel == "h2":
                first.count = AsyncMock(return_value=1)
                first.text_content = AsyncMock(return_value="Senior QA Engineer")
            elif "company" in sel:
                first.count = AsyncMock(return_value=1)
                first.text_content = AsyncMock(return_value="Acme Corp")
            elif "location" in sel:
                first.count = AsyncMock(return_value=1)
                first.text_content = AsyncMock(return_value="Seattle, WA")
            elif sel == "a":
                first.count = AsyncMock(return_value=1)
                first.get_attribute = AsyncMock(return_value="/jobs/detail/101")
            else:
                first.count = AsyncMock(return_value=0)
            loc.first = first
            loc.all = AsyncMock(return_value=[first])
            return loc

        mock_card.locator.side_effect = card_locator_side_effect

        # Mock find_fallback_cards returning article cards
        with patch("scripts.auto_scour.find_fallback_cards", new_callable=AsyncMock) as mock_fallback:
            mock_fallback.return_value = ("article", [mock_card])
            with patch("scripts.auto_scour.is_likely_job_url", return_value=True):
                config = {
                    "search_url": "https://example.com/search?q={search_term}",
                    "job_card_selector": ".obsolete-card-class",
                    "title_selector": ".obsolete-title",
                    "company_selector": ".obsolete-company",
                    "job_url_selector": "a.obsolete-link"
                }
                semaphore = AsyncMock()

                jobs = await scrape_site(mock_context, "ModernTech", {}, config, "QA", "Seattle", semaphore, telemetry=telemetry)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Senior QA Engineer")
        self.assertEqual(jobs[0]["company"], "Acme Corp")
        self.assertIn("/jobs/detail/101", jobs[0]["url"])

        # Check telemetry
        self.assertEqual(len(telemetry.selector_drifts), 1)
        drift = telemetry.selector_drifts[0]
        self.assertEqual(drift["drift_type"], "card_selector")
        self.assertTrue(drift["rescued"])
        self.assertEqual(drift["rescued_count"], 1)

    async def test_scrape_site_card_drift_hard_failure(self):
        telemetry = ScourTelemetry()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.close = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto = AsyncMock(return_value=mock_response)
        mock_page.title = AsyncMock(return_value="Empty Portal")
        mock_page.evaluate = AsyncMock(return_value="No jobs")
        mock_page.url = "https://example.com/search?q=QA"
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("Timeout"))

        with patch("scripts.auto_scour.find_fallback_cards", new_callable=AsyncMock) as mock_fallback:
            mock_fallback.return_value = (None, [])
            config = {
                "search_url": "https://example.com/search?q={search_term}",
                "job_card_selector": ".defunct-selector"
            }
            semaphore = AsyncMock()
            jobs = await scrape_site(mock_context, "DefunctSite", {}, config, "QA", "Seattle", semaphore, telemetry=telemetry)

        self.assertEqual(len(jobs), 0)
        self.assertEqual(len(telemetry.selector_drifts), 1)
        drift = telemetry.selector_drifts[0]
        self.assertEqual(drift["drift_type"], "card_selector")
        self.assertFalse(drift["rescued"])

    async def test_scrape_site_drops_poisoned_search_url_links(self):
        telemetry = ScourTelemetry()
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.close = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto = AsyncMock(return_value=mock_response)
        mock_page.title = AsyncMock(return_value="Job Portal")
        mock_page.evaluate = AsyncMock(return_value="Job Portal Listings")
        mock_page.url = "https://example.com/search?q=QA"

        mock_card = MagicMock()
        mock_card.text_content = AsyncMock(return_value="QA Engineer")
        mock_card.evaluate = AsyncMock(return_value="div")

        # Card has NO link (e.g., link selector fails or returns search url)
        def card_locator_side_effect(sel):
            loc = MagicMock()
            first = MagicMock()
            if "title" in sel:
                first.count = AsyncMock(return_value=1)
                first.text_content = AsyncMock(return_value="QA Engineer")
            else:
                first.count = AsyncMock(return_value=0)
            loc.first = first
            loc.all = AsyncMock(return_value=[])
            return loc

        mock_card.locator.side_effect = card_locator_side_effect

        mock_page.wait_for_selector = AsyncMock()
        mock_page.locator.return_value.all = AsyncMock(return_value=[mock_card])

        config = {
            "search_url": "https://example.com/search?q={search_term}",
            "job_card_selector": ".job-card",
            "title_selector": ".job-title",
            "job_url_selector": ".broken-link"
        }
        semaphore = AsyncMock()

        # extract_fallback_link fails to find any distinct job link
        with patch("scripts.auto_scour.extract_fallback_link", new_callable=AsyncMock, return_value=None):
            jobs = await scrape_site(mock_context, "TestSite", {}, config, "QA", "Seattle", semaphore, telemetry=telemetry)

        # Card was dropped to protect Phase 2 from search URL poisoning!
        self.assertEqual(len(jobs), 0)
        self.assertEqual(len(telemetry.selector_drifts), 1)
        self.assertEqual(telemetry.selector_drifts[0]["drift_type"], "link_selector")

if __name__ == "__main__":
    unittest.main()
