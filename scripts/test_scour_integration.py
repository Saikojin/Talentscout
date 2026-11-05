import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from scripts.scour_telemetry import ScourTelemetry
from scripts.pagination_utils import build_page_url

class TestScourIntegration(unittest.TestCase):
    def setUp(self):
        self.telemetry = ScourTelemetry()

    def test_cli_argument_parsing(self):
        from scripts.auto_scour import parse_args
        args = parse_args(["--page", "3", "--skip-page-one", "--detect-pages-only", "--dry-run"])
        self.assertEqual(args.page, 3)
        self.assertTrue(args.skip_page_one)
        self.assertTrue(args.detect_pages_only)
        self.assertTrue(args.dry_run)
        self.assertEqual(args.max_pages, 1)

    def test_cli_defaults(self):
        from scripts.auto_scour import parse_args
        args = parse_args([])
        self.assertEqual(args.page, 1)
        self.assertFalse(args.skip_page_one)
        self.assertFalse(args.detect_pages_only)
        self.assertFalse(args.dry_run)
        self.assertEqual(args.max_pages, 1)

    def test_page_url_construction_in_scour(self):
        base_url = "https://builtin.com/jobs/seattle?search=QA"
        config = {"pagination_type": "page_param", "page_param": "page"}
        
        # When page is 2
        url_p2 = build_page_url(base_url, config, page_num=2)
        self.assertIn("page=2", url_p2)

        # When page is 1
        url_p1 = build_page_url(base_url, config, page_num=1)
        self.assertEqual(url_p1, base_url)

    def test_telemetry_recording_flow(self):
        # Simulate discovering, processing, blocking, and rejections
        self.telemetry.record_job_discovered(10)
        self.telemetry.record_block("Dice", "https://dice.com", "HTTP 403 Forbidden")
        self.telemetry.record_blacklist_skip("banned.com")
        self.telemetry.record_rejection("Test Title", "Test Co", ["Foreign Country: India"])
        self.telemetry.record_page_count("BuiltIn", 4, 80)
        self.telemetry.record_job_processed(5)
        self.telemetry.record_job_passed(2)

        summary = self.telemetry.format_summary()
        self.assertIn("SCOUR SUMMARY REPORT", summary)
        self.assertIn("Dice", summary)
        self.assertIn("banned.com", summary)
        self.assertIn("Location / Foreign Country", summary)
        self.assertIn("BuiltIn", summary)

if __name__ == "__main__":
    unittest.main()
