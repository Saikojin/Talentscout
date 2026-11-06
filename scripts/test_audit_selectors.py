import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from scripts.audit_selectors import audit_single_site, format_audit_report

class TestAuditSelectors(unittest.IsolatedAsyncioTestCase):
    async def test_audit_single_site_pass(self):
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.close = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto = AsyncMock(return_value=mock_response)
        mock_page.title = AsyncMock(return_value="Job Search")
        mock_page.evaluate = AsyncMock(return_value="Listing 1 to 20")
        mock_page.url = "https://example.com/jobs?q=QA"

        # Mock 1 card found
        mock_card = MagicMock()
        mock_card.evaluate = AsyncMock(return_value="div")
        
        def card_locator_side_effect(sel):
            loc = MagicMock()
            first = MagicMock()
            if sel == "h2":
                first.count = AsyncMock(return_value=1)
                first.text_content = AsyncMock(return_value="Lead QA Engineer")
            elif sel == "a.title-link":
                first.count = AsyncMock(return_value=1)
                first.get_attribute = AsyncMock(return_value="/jobs/detail/4432")
                first.evaluate = AsyncMock(return_value="/jobs/detail/4432")
            elif sel == ".company":
                first.count = AsyncMock(return_value=1)
                first.text_content = AsyncMock(return_value="Acme Corp")
            else:
                first.count = AsyncMock(return_value=0)
            loc.first = first
            return loc

        mock_card.locator.side_effect = card_locator_side_effect

        mock_page.wait_for_selector = AsyncMock()
        mock_page.locator.return_value.all = AsyncMock(return_value=[mock_card])

        config = {
            "search_url": "https://example.com/jobs?q={search_term}",
            "job_card_selector": "article.job",
            "title_selector": "h2",
            "company_selector": ".company",
            "job_url_selector": "a.title-link"
        }

        with patch("scripts.audit_selectors.is_likely_job_url", return_value=True):
            res = await audit_single_site(mock_context, "AcmeJobs", config, keyword="QA", timeout_ms=5000)

        self.assertEqual(res["status"], "PASS")
        self.assertEqual(res["cards_found"], 1)
        self.assertEqual(res["sample_title"], "Lead QA Engineer")
        self.assertEqual(res["sample_company"], "Acme Corp")
        self.assertEqual(res["sample_url"], "https://example.com/jobs/detail/4432")

    async def test_audit_single_site_drift_card(self):
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.close = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto = AsyncMock(return_value=mock_response)
        mock_page.title = AsyncMock(return_value="Job Search")
        mock_page.evaluate = AsyncMock(return_value="No jobs found")
        mock_page.url = "https://example.com/jobs?q=QA"

        # Primary selector fails
        mock_page.wait_for_selector = AsyncMock(side_effect=Exception("Timeout"))

        config = {
            "search_url": "https://example.com/jobs?q={search_term}",
            "job_card_selector": ".obsolete-class"
        }

        with patch("scripts.audit_selectors.find_fallback_cards", new_callable=AsyncMock, return_value=("article", [MagicMock()])):
            res = await audit_single_site(mock_context, "ObsoleteSite", config, keyword="QA", timeout_ms=5000)

        self.assertEqual(res["status"], "DRIFT_CARD")
        self.assertEqual(res["fallback_card_selector"], "article")
        self.assertEqual(res["fallback_cards_found"], 1)

    def test_format_audit_report(self):
        results = [
            {"site": "Dice", "status": "PASS", "cards_found": 20, "sample_title": "QA Engineer", "details": "Healthy"},
            {"site": "Microsoft", "status": "DRIFT_CARD", "cards_found": 0, "sample_title": None, "details": "0 cards found"},
            {"site": "Google", "status": "DRIFT_LINK", "cards_found": 15, "sample_title": "QA Lead", "details": "URL matched search page"},
        ]
        report = format_audit_report(results)
        self.assertIn("DOM SELECTOR AUDIT REPORT", report)
        self.assertIn("Dice", report)
        self.assertIn("Microsoft", report)
        self.assertIn("Google", report)
        self.assertIn("TOTAL AUDITED: 3 | PASS: 1 | DRIFT: 2", report)

if __name__ == "__main__":
    unittest.main()
