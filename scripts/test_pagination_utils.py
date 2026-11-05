import unittest
from scripts.pagination_utils import (
    extract_page_count,
    build_page_url,
)

class TestPaginationUtils(unittest.TestCase):
    def test_extract_page_count_from_page_of_text(self):
        text = "Search results for QA in Seattle. Page 1 of 8. Showing latest openings."
        res = extract_page_count(text)
        self.assertEqual(res["page_count"], 8)

    def test_extract_page_count_from_range_and_total_jobs(self):
        text = "Showing 1 - 25 of 175 jobs for Senior QA Engineer"
        res = extract_page_count(text, items_per_page=25)
        self.assertEqual(res["total_jobs"], 175)
        self.assertEqual(res["page_count"], 7)

    def test_extract_page_count_from_comma_formatted_total(self):
        text = "Showing 1 to 20 of 1,200 open positions"
        res = extract_page_count(text, items_per_page=20)
        self.assertEqual(res["total_jobs"], 1200)
        self.assertEqual(res["page_count"], 60)

    def test_extract_page_count_from_pagination_links(self):
        text = "No direct text pattern here"
        elements = ["1", "2", "3", "4", "5", "Next >"]
        res = extract_page_count(text, pagination_elements=elements)
        self.assertEqual(res["page_count"], 5)

    def test_extract_page_count_fallback_single_page(self):
        text = "Just a regular job page with 5 jobs and no pagination."
        res = extract_page_count(text)
        self.assertEqual(res["page_count"], 1)
        self.assertIsNone(res["total_jobs"])

    def test_build_page_url_page_one_returns_original(self):
        url = "https://builtin.com/jobs/seattle?search=QA"
        config = {"pagination_type": "page_param", "page_param": "page"}
        res = build_page_url(url, config, page_num=1)
        self.assertEqual(res, url)

    def test_build_page_url_page_param(self):
        url = "https://builtin.com/jobs/seattle?search=QA"
        config = {"pagination_type": "page_param", "page_param": "page"}
        res = build_page_url(url, config, page_num=3)
        self.assertIn("search=QA", res)
        self.assertIn("page=3", res)

    def test_build_page_url_offset(self):
        url = "https://www.linkedin.com/jobs/search?keywords=QA&location=Seattle"
        config = {
            "pagination_type": "offset",
            "offset_param": "start",
            "items_per_page": 25
        }
        res = build_page_url(url, config, page_num=2)
        self.assertIn("start=25", res)

        res3 = build_page_url(url, config, page_num=3)
        self.assertIn("start=50", res3)

    def test_build_page_url_heuristics_builtin(self):
        url = "https://builtin.com/jobs/seattle?search=QA"
        config = {} # empty config, should deduce page param
        res = build_page_url(url, config, page_num=2, site_name="BuiltIn")
        self.assertIn("page=2", res)

    def test_build_page_url_heuristics_indeed(self):
        url = "https://www.indeed.com/jobs?q=QA&l=Seattle"
        config = {}
        res = build_page_url(url, config, page_num=3, site_name="Indeed")
        self.assertIn("start=20", res)

if __name__ == "__main__":
    unittest.main()
