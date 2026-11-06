import unittest
import os
import json
import tempfile
from scripts.scour_telemetry import (
    ScourTelemetry,
    detect_http_block,
    detect_dom_challenge,
)

class TestScourTelemetry(unittest.TestCase):
    def setUp(self):
        self.telemetry = ScourTelemetry()

    def test_detect_http_block_codes(self):
        self.assertEqual(detect_http_block(403), "HTTP 403 Forbidden")
        self.assertEqual(detect_http_block(429), "HTTP 429 Rate Limited")
        self.assertEqual(detect_http_block(503), "HTTP 503 Service Unavailable")
        self.assertIsNone(detect_http_block(200))
        self.assertIsNone(detect_http_block(301))
        self.assertIsNone(detect_http_block(404))

    def test_detect_dom_challenge_cloudflare(self):
        title = "Just a moment..."
        body = "Checking your browser before accessing example.com. Cloudflare Ray ID: 12345"
        self.assertEqual(detect_dom_challenge(title, body, "https://example.com"), "Cloudflare Challenge")

    def test_detect_dom_challenge_turnstile_captcha(self):
        title = "Security Check"
        body = "Please verify you are a human to continue. Cloudflare Turnstile verification."
        self.assertEqual(detect_dom_challenge(title, body, "https://example.com"), "Cloudflare Turnstile")

    def test_detect_dom_challenge_login_wall(self):
        title = "LinkedIn: Log In or Sign Up"
        body = "Sign in to view jobs"
        url = "https://www.linkedin.com/login?from=jobs"
        self.assertEqual(detect_dom_challenge(title, body, url), "LinkedIn Login Wall")

    def test_detect_dom_challenge_clean_page(self):
        title = "Software Engineer Jobs in Seattle"
        body = "Showing 25 jobs. Senior QA Engineer at Contoso, Remote."
        url = "https://example.com/jobs"
        self.assertIsNone(detect_dom_challenge(title, body, url))

    def test_record_block(self):
        self.telemetry.record_block("Dice", "https://dice.com/jobs", "HTTP 403 Forbidden", "Access denied by WAF")
        self.assertEqual(len(self.telemetry.blocks), 1)
        self.assertEqual(self.telemetry.blocks[0]["site"], "Dice")
        self.assertEqual(self.telemetry.blocks[0]["block_type"], "HTTP 403 Forbidden")
        self.assertTrue(self.telemetry.has_blocks())

    def test_record_blacklist(self):
        self.telemetry.record_blacklist_skip("dailyremote.com", "Domain blacklisted")
        self.telemetry.record_blacklist_skip("playgendary.com", "Domain blacklisted")
        self.assertEqual(len(self.telemetry.blacklist_skips), 2)

    def test_record_rejection_categorization(self):
        self.telemetry.record_rejection("QA Tester", "Globex", ["Foreign Country: Pakistan"])
        self.telemetry.record_rejection("DevOps", "Initech", ["Disqualified Skill: Cobol"])
        self.telemetry.record_rejection("Junior Intern", "Umbrella", ["Negative Title: intern"])
        self.telemetry.record_rejection("Unknown", "Acme", ["SafetyNet: Empty or invalid job description"])
        self.telemetry.record_rejection("Staff QA", "Hooli", ["Low Score: 35/100"])

        stats = self.telemetry.get_rejection_stats()
        self.assertEqual(stats["Location / Foreign Country"], 1)
        self.assertEqual(stats["Disqualified Skill"], 1)
        self.assertEqual(stats["Negative Title Keyword"], 1)
        self.assertEqual(stats["Empty JD SafetyNet"], 1)
        self.assertEqual(stats["Low Score"], 1)
        self.assertEqual(self.telemetry.total_rejections(), 5)

    def test_record_page_count(self):
        self.telemetry.record_page_count("BuiltIn", page_count=8, total_jobs=192)
        self.telemetry.record_page_count("Dice", page_count=4, total_jobs=90)
        self.assertEqual(self.telemetry.page_counts["BuiltIn"]["page_count"], 8)
        self.assertEqual(self.telemetry.page_counts["BuiltIn"]["total_jobs"], 192)

    def test_record_selector_drift(self):
        # 1. Card drift (failed)
        self.telemetry.record_selector_drift(
            "Microsoft Careers",
            "https://careers.microsoft.com",
            "card_selector",
            "div.job-tile",
            "0 cards matched",
            rescued=False
        )
        # 2. Card drift (rescued)
        self.telemetry.record_selector_drift(
            "Wellfound",
            "https://wellfound.com/jobs",
            "card_selector",
            ".startup-card",
            "Rescued via heuristics",
            rescued=True,
            rescued_count=15
        )
        # 3. Link drift
        self.telemetry.record_selector_drift(
            "Google Careers",
            "https://www.google.com/about/careers/applications/jobs/results",
            "link_selector",
            "a.gc-card__title",
            "No direct href found, avoided search URL fallback"
        )
        # 4. Title drift
        self.telemetry.record_selector_drift(
            "ZipRecruiter",
            "https://ziprecruiter.com/jobs",
            "title_selector",
            "h2.title",
            "Fell back to 'Unknown Title'"
        )

        drift_stats = self.telemetry.get_drift_stats()
        self.assertEqual(drift_stats["card_selector"], 2)
        self.assertEqual(drift_stats["link_selector"], 1)
        self.assertEqual(drift_stats["title_selector"], 1)
        self.assertEqual(drift_stats["company_selector"], 0)
        self.assertEqual(drift_stats["rescued_sites"], 1)
        self.assertEqual(drift_stats["rescued_jobs"], 15)
        self.assertEqual(drift_stats["total_drifts"], 4)
        self.assertEqual(self.telemetry.total_drifts(), 4)

        summary_text = self.telemetry.format_summary()
        self.assertIn("DOM SELECTOR DRIFT DETECTED", summary_text)
        self.assertIn("Microsoft Careers", summary_text)
        self.assertIn("Wellfound", summary_text)
        self.assertIn("Rescued 15 jobs", summary_text)

    def test_summary_and_json_export(self):
        self.telemetry.record_job_discovered(50)
        self.telemetry.record_job_processed(30)
        self.telemetry.record_job_passed(10)
        self.telemetry.record_block("Glassdoor", "https://glassdoor.com", "HTTP 403 Forbidden")
        self.telemetry.record_rejection("QA Lead", "Apex", ["Disqualified Skill: Java"])
        self.telemetry.record_page_count("BuiltIn", 5, 120)
        self.telemetry.record_selector_drift("Indeed", "https://indeed.com", "card_selector", ".job_seen_beacon", "0 cards")

        summary_text = self.telemetry.format_summary()
        self.assertIn("SCOUR SUMMARY REPORT", summary_text)
        self.assertIn("Glassdoor", summary_text)
        self.assertIn("HTTP 403 Forbidden", summary_text)
        self.assertIn("Disqualified Skill", summary_text)
        self.assertIn("BuiltIn", summary_text)
        self.assertIn("DOM SELECTOR DRIFT DETECTED", summary_text)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = os.path.join(tmpdir, "telemetry.json")
            self.telemetry.save_json(out_file)
            self.assertTrue(os.path.exists(out_file))
            with open(out_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["yield"]["discovered"], 50)
            self.assertEqual(data["yield"]["passed"], 10)
            self.assertEqual(len(data["selector_drifts"]), 1)
            self.assertEqual(data["drift_stats"]["card_selector"], 1)

if __name__ == "__main__":
    unittest.main()
