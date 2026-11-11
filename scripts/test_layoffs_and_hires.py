import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from scripts.selector_heuristics import is_likely_job_url
from scripts.ingest_layoffs_and_hires import detect_ats_type, query_hiring_for_term, LAYOFFS_HIRES_CONFIG
from scripts.audit_selectors import audit_single_site


class TestLayoffsAndHiresIntegration(unittest.TestCase):
    def test_config_contract(self):
        """Verify that LAYOFFS_HIRES_CONFIG contains all required selectors."""
        required_keys = [
            "search_url", "search_input_selector", "expand_button_selector",
            "job_card_selector", "title_selector", "company_selector",
            "job_url_selector", "is_career_directory"
        ]
        for k in required_keys:
            self.assertIn(k, LAYOFFS_HIRES_CONFIG)
            self.assertTrue(LAYOFFS_HIRES_CONFIG[k], f"Key {k} must not be empty")

        self.assertTrue(LAYOFFS_HIRES_CONFIG["is_career_directory"])

    def test_detect_ats_type(self):
        """Verify that ATS type detection accurately categorizes known ATS domains."""
        self.assertEqual(detect_ats_type("https://hpe.wd5.myworkdayjobs.com/acjobsite")[0], "workday")
        self.assertEqual(detect_ats_type("https://job-boards.greenhouse.io/capco")[0], "greenhouse")
        self.assertEqual(detect_ats_type("https://jobs.lever.co/ajax")[0], "lever")
        self.assertEqual(detect_ats_type("https://jobs.ashbyhq.com/logiqal")[0], "ashby")
        self.assertEqual(detect_ats_type("https://apply.workable.com/msr-fsr/")[0], "workable")
        self.assertIsNone(detect_ats_type("https://example.com/careers")[0])

    def test_is_likely_job_url_with_career_portals(self):
        """Ensure Workday/Greenhouse/Lever URLs pass validation when career portals are allowed."""
        base = "https://layoffsandhires.com/"
        self.assertTrue(is_likely_job_url("https://hpe.wd5.myworkdayjobs.com/acjobsite?q=QA", base, allow_career_portals=True))
        self.assertTrue(is_likely_job_url("https://job-boards.greenhouse.io/capco", base, allow_career_portals=True))
        self.assertTrue(is_likely_job_url("https://jobs.lever.co/ajax", base, allow_career_portals=True))
        self.assertTrue(is_likely_job_url("https://jobs.ashbyhq.com/logiqal", base, allow_career_portals=True))
        # Self-referencing link or non-job URLs should still be rejected
        self.assertFalse(is_likely_job_url("https://layoffsandhires.com/", base, allow_career_portals=True))
        self.assertFalse(is_likely_job_url("mailto:support@layoffsandhires.com", base, allow_career_portals=True))


class TestLayoffsAndHiresAsync(unittest.IsolatedAsyncioTestCase):
    async def test_audit_single_site_with_input_and_expand(self):
        """Test audit_single_site handling of dynamic input typing and results pane expansion."""
        mock_context = MagicMock()
        mock_page = MagicMock()
        mock_page.close = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto = AsyncMock(return_value=mock_response)
        mock_page.title = AsyncMock(return_value="Layoffs & Hires")
        mock_page.evaluate = AsyncMock(return_value="Hiring for QA")
        mock_page.url = "https://layoffsandhires.com/"

        # Mock search input
        mock_input = MagicMock()
        mock_input.count = AsyncMock(return_value=1)
        mock_input.fill = AsyncMock()

        # Mock expand button
        mock_expand_btn = MagicMock()
        mock_expand_btn.count = AsyncMock(return_value=1)
        mock_expand_btn.click = AsyncMock()

        # Mock cards
        mock_card_1 = MagicMock()
        mock_card_1.evaluate = AsyncMock(return_value="li")
        
        def card_locator_side_effect(sel):
            loc = MagicMock()
            first = MagicMock()
            if "matches-name" in sel:
                first.count = AsyncMock(return_value=1)
                first.text_content = AsyncMock(return_value="Acme Corp")
            elif sel == "a":
                first.count = AsyncMock(return_value=1)
                first.get_attribute = AsyncMock(return_value="https://acme.wd5.myworkdayjobs.com/careers?q=QA")
            else:
                first.count = AsyncMock(return_value=0)
            loc.first = first
            return loc

        mock_card_1.locator.side_effect = card_locator_side_effect

        def page_locator_side_effect(sel):
            loc = MagicMock()
            if "search" in sel or "placeholder" in sel:
                loc.first = mock_input
            elif "matches-more" in sel:
                loc.first = mock_expand_btn
            elif "matches-list" in sel:
                loc.all = AsyncMock(return_value=[mock_card_1])
            return loc

        mock_page.locator.side_effect = page_locator_side_effect
        mock_page.wait_for_selector = AsyncMock()

        res = await audit_single_site(mock_context, "Layoffs & Hires", LAYOFFS_HIRES_CONFIG, keyword="QA")

        self.assertEqual(res["status"], "PASS")
        self.assertEqual(res["cards_found"], 1)
        self.assertEqual(res["sample_company"], "Acme Corp")
        self.assertIn("myworkdayjobs.com", res["sample_url"])
        mock_input.fill.assert_awaited_once_with("QA")
        mock_expand_btn.click.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
