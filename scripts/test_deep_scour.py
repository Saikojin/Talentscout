import unittest
import sys
from scripts.scour_deep import parse_deep_args

class TestDeepScour(unittest.TestCase):
    def test_default_deep_args(self):
        args = parse_deep_args([])
        self.assertEqual(args.page, 2)
        self.assertTrue(args.skip_page_one)
        self.assertEqual(args.max_pages, 1)
        self.assertFalse(args.detect_pages_only)
        self.assertFalse(args.dry_run)

    def test_custom_page_deep_args(self):
        args = parse_deep_args(["--page", "5", "--max-pages", "2", "--dry-run"])
        self.assertEqual(args.page, 5)
        self.assertTrue(args.skip_page_one)
        self.assertEqual(args.max_pages, 2)
        self.assertTrue(args.dry_run)

    def test_detect_pages_only_arg(self):
        args = parse_deep_args(["--detect-pages-only"])
        self.assertTrue(args.detect_pages_only)
        self.assertTrue(args.skip_page_one)

if __name__ == "__main__":
    unittest.main()
