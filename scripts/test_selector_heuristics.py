import unittest
from unittest.mock import AsyncMock, MagicMock
from scripts.selector_heuristics import (
    is_likely_job_url,
    find_fallback_cards,
    extract_fallback_title,
    extract_fallback_link,
    extract_fallback_company,
    extract_fallback_location,
    FALLBACK_CARD_SELECTORS,
)

class TestSelectorHeuristics(unittest.TestCase):
    def test_is_likely_job_url_positive(self):
        base_url = "https://example.com/jobs/search?q=QA&l=Seattle"
        self.assertTrue(is_likely_job_url("/jobs/view/123456", base_url))
        self.assertTrue(is_likely_job_url("https://example.com/careers/posting/sdet-senior", base_url))
        self.assertTrue(is_likely_job_url("/position/lead-qa-engineer?gh_jid=9988", base_url))
        self.assertTrue(is_likely_job_url("https://boards.greenhouse.io/acme/jobs/401239", base_url))
        self.assertTrue(is_likely_job_url("/job/982341", base_url))

    def test_is_likely_job_url_negative_search_self_reference(self):
        base_url = "https://example.com/jobs/search?q=QA&l=Seattle"
        # Same URL as base search page
        self.assertFalse(is_likely_job_url("https://example.com/jobs/search?q=QA&l=Seattle", base_url))
        self.assertFalse(is_likely_job_url("/jobs/search?q=QA&l=Seattle", base_url))
        self.assertFalse(is_likely_job_url("/jobs/search", base_url))

    def test_is_likely_job_url_negative_non_job(self):
        base_url = "https://example.com/jobs"
        self.assertFalse(is_likely_job_url("", base_url))
        self.assertFalse(is_likely_job_url("#", base_url))
        self.assertFalse(is_likely_job_url("javascript:void(0)", base_url))
        self.assertFalse(is_likely_job_url("/login?next=/jobs", base_url))
        self.assertFalse(is_likely_job_url("/privacy-policy", base_url))
        self.assertFalse(is_likely_job_url("mailto:support@example.com", base_url))

class TestSelectorHeuristicsAsync(unittest.IsolatedAsyncioTestCase):
    async def test_find_fallback_cards_found(self):
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_card_1 = MagicMock()
        mock_card_2 = MagicMock()

        # Simulate page.locator("article") returns 2 cards
        def locator_side_effect(sel):
            loc = MagicMock()
            if sel == "article":
                loc.count = AsyncMock(return_value=2)
                loc.all = AsyncMock(return_value=[mock_card_1, mock_card_2])
            else:
                loc.count = AsyncMock(return_value=0)
                loc.all = AsyncMock(return_value=[])
            return loc

        mock_page.locator.side_effect = locator_side_effect

        sel, cards = await find_fallback_cards(mock_page)
        self.assertEqual(sel, "article")
        self.assertEqual(len(cards), 2)

    async def test_find_fallback_cards_none_found(self):
        mock_page = MagicMock()
        def locator_side_effect(sel):
            loc = MagicMock()
            loc.count = AsyncMock(return_value=0)
            loc.all = AsyncMock(return_value=[])
            return loc

        mock_page.locator.side_effect = locator_side_effect

        sel, cards = await find_fallback_cards(mock_page)
        self.assertIsNone(sel)
        self.assertEqual(cards, [])

    async def test_extract_fallback_title(self):
        mock_card = MagicMock()
        def locator_side_effect(sel):
            loc = MagicMock()
            first = MagicMock()
            if sel == "h2":
                first.count = AsyncMock(return_value=1)
                first.text_content = AsyncMock(return_value="  Senior QA Automation Engineer  ")
            else:
                first.count = AsyncMock(return_value=0)
                first.text_content = AsyncMock(return_value="")
            loc.first = first
            return loc

        mock_card.locator.side_effect = locator_side_effect

        title = await extract_fallback_title(mock_card)
        self.assertEqual(title, "Senior QA Automation Engineer")

    async def test_extract_fallback_link_from_anchor_card(self):
        mock_card = MagicMock()
        mock_card.evaluate = AsyncMock(return_value="a")
        mock_card.get_attribute = AsyncMock(return_value="/jobs/detail/10928")

        link = await extract_fallback_link(mock_card, "https://example.com/jobs")
        self.assertEqual(link, "https://example.com/jobs/detail/10928")

    async def test_extract_fallback_link_from_child_anchor(self):
        mock_card = MagicMock()
        mock_card.evaluate = AsyncMock(return_value="div")

        link_nav = MagicMock()
        link_nav.get_attribute = AsyncMock(return_value="/search?q=QA")

        link_job = MagicMock()
        link_job.get_attribute = AsyncMock(return_value="/jobs/view/99912")

        mock_locator = MagicMock()
        mock_locator.all = AsyncMock(return_value=[link_nav, link_job])
        mock_card.locator.return_value = mock_locator

        link = await extract_fallback_link(mock_card, "https://example.com/jobs/search?q=QA")
        self.assertEqual(link, "https://example.com/jobs/view/99912")

    async def test_extract_fallback_company(self):
        mock_card = MagicMock()
        def locator_side_effect(sel):
            loc = MagicMock()
            first = MagicMock()
            if sel == "[data-testid*='company']":
                first.count = AsyncMock(return_value=1)
                first.text_content = AsyncMock(return_value="Acme Corp")
            else:
                first.count = AsyncMock(return_value=0)
            loc.first = first
            return loc

        mock_card.locator.side_effect = locator_side_effect

        company = await extract_fallback_company(mock_card)
        self.assertEqual(company, "Acme Corp")

    async def test_extract_fallback_location(self):
        mock_card = MagicMock()
        def locator_side_effect(sel):
            loc = MagicMock()
            first = MagicMock()
            if sel == ".job-location":
                first.count = AsyncMock(return_value=1)
                first.text_content = AsyncMock(return_value="Seattle, WA (Hybrid)")
            else:
                first.count = AsyncMock(return_value=0)
            loc.first = first
            return loc

        mock_card.locator.side_effect = locator_side_effect

        loc = await extract_fallback_location(mock_card)
        self.assertEqual(loc, "Seattle, WA (Hybrid)")

if __name__ == "__main__":
    unittest.main()
