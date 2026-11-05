import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from scripts.browser_stealth import (
    get_stealth_context_options,
    create_stealth_context,
    resolve_transient_challenge,
    STEALTH_JS,
)

class TestBrowserStealth(unittest.TestCase):
    def test_get_stealth_context_options_defaults(self):
        opts = get_stealth_context_options()
        self.assertIn("user_agent", opts)
        self.assertIn("Chrome/128", opts["user_agent"])
        self.assertEqual(opts["viewport"]["width"], 1920)
        self.assertEqual(opts["viewport"]["height"], 1080)
        self.assertEqual(opts["locale"], "en-US")
        self.assertEqual(opts["timezone_id"], "America/Los_Angeles")

        headers = opts["extra_http_headers"]
        self.assertEqual(headers["sec-ch-ua-platform"], '"Windows"')
        self.assertEqual(headers["sec-ch-ua-mobile"], "?0")
        self.assertIn("en-US", headers["accept-language"])

    def test_get_stealth_context_options_custom_ua(self):
        custom_ua = "CustomUserAgent/1.0"
        opts = get_stealth_context_options(user_agent=custom_ua)
        self.assertEqual(opts["user_agent"], custom_ua)

    def test_stealth_js_contains_critical_evasions(self):
        self.assertIn("navigator, 'webdriver'", STEALTH_JS)
        self.assertIn("window.chrome", STEALTH_JS)
        self.assertIn("navigator, 'plugins'", STEALTH_JS)
        self.assertIn("navigator, 'languages'", STEALTH_JS)
        self.assertIn("permissions.query", STEALTH_JS)

    def test_create_stealth_context_initialization(self):
        async def run_test():
            mock_browser = MagicMock()
            mock_context = AsyncMock()
            mock_browser.new_context = AsyncMock(return_value=mock_context)

            ctx = await create_stealth_context(mock_browser)
            self.assertEqual(ctx, mock_context)
            mock_browser.new_context.assert_called_once()
            mock_context.add_init_script.assert_called_once_with(STEALTH_JS)

        asyncio.run(run_test())

    def test_resolve_transient_challenge_no_challenge_returns_true(self):
        async def run_test():
            mock_page = AsyncMock()
            mock_page.title = AsyncMock(return_value="Senior QA Engineer Jobs")
            mock_page.evaluate = AsyncMock(return_value="Welcome to the jobs portal. Listing 25 jobs.")

            resolved = await resolve_transient_challenge(mock_page, timeout_seconds=2)
            self.assertTrue(resolved)

        asyncio.run(run_test())

    def test_resolve_transient_challenge_resolves_after_delay(self):
        async def run_test():
            mock_page = AsyncMock()
            call_count = 0

            async def fake_title():
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    return "Just a moment..."
                return "Jobs Portal - Active Openings"

            mock_page.title = fake_title
            mock_page.evaluate = AsyncMock(return_value="Checking your browser...")

            resolved = await resolve_transient_challenge(mock_page, timeout_seconds=4, poll_interval=0.1)
            self.assertTrue(resolved)
            self.assertGreater(call_count, 2)

        asyncio.run(run_test())

    def test_resolve_transient_challenge_fails_if_persisting(self):
        async def run_test():
            mock_page = AsyncMock()
            mock_page.title = AsyncMock(return_value="Attention Required! | Cloudflare")
            mock_page.evaluate = AsyncMock(return_value="Please verify you are a human to continue.")

            resolved = await resolve_transient_challenge(mock_page, timeout_seconds=0.3, poll_interval=0.1)
            self.assertFalse(resolved)

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
