import unittest
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.scorer import score_job
from scripts.location_utils import evaluate_job_location

class TestLocationHardening(unittest.TestCase):

    def test_riot_games_singapore(self):
        jd = "QA Engineer II - Unpublished R&D Product (Contract) Riot Games Singapore, Central Singapore, Singapore. 23 days ago. Apply Save Riot Games was established in 2006."
        res = score_job(jd, title="QA Engineer II - Unpublished R&D Product (Contract)", location="", company="Riot Games", url="https://gamejobs.co/QA-Engineer-II-Unpublished-R-D-Product-Contract-at-Riot-Games")
        self.assertTrue(res["is_disqualified"], f"Expected disqualified, got {res}")
        self.assertTrue(any("Singapore" in r or "Non-US" in r for r in res["disqualified_by"]))

    def test_dice_indiana_hybrid(self):
        jd = "QA ENGINEER - AaraTechnologies Inc - Hybrid in Michigan City, IN, US | Dice.com. QA Analyst Healthcare (2-3 Years Experience). On-site contract."
        res = score_job(jd, title="QA ENGINEER", location="", company="AaraTechnologies Inc", url="https://www.dice.com/job-detail/f9aec316-5b66-455b-8b4e-ceb138ca5b21")
        self.assertTrue(res["is_disqualified"], f"Expected disqualified, got {res}")
        self.assertTrue(any("Indiana" in r or "WA" in r for r in res["disqualified_by"]))

    def test_veeam_pakistan(self):
        jd = "Senior SDET position at Veeam Software. Work with QA automation and backend testing tools in Islamabad."
        res = score_job(jd, title="Senior SDET", location="Islamabad, Pakistan", company="Veeam Software", url="https://job-boards.eu.greenhouse.io/veeamsoftware/jobs/4856149101")
        self.assertTrue(res["is_disqualified"], f"Expected disqualified, got {res}")
        self.assertTrue(any("Pakistan" in r or "Non-US" in r for r in res["disqualified_by"]))

    def test_veeam_qatar_remote(self):
        jd = "Technical Account Manager at Veeam Software in Qatar. Coordinate customer requirements and technical quality."
        res = score_job(jd, title="Technical Account Manager - Qatar", location="Remote, Qatar", company="Veeam Software", url="https://job-boards.eu.greenhouse.io/veeamsoftware/jobs/4889155101")
        self.assertTrue(res["is_disqualified"], f"Expected disqualified, got {res}")
        self.assertTrue(any("Qatar" in r or "Non-US" in r for r in res["disqualified_by"]))

    def test_evolution_atlantic_city_nj(self):
        jd = "Card Inspector (Quality Assurance) in Atlantic City, NJ. Evolution is a leading company of virtual casino games. We offer nationwide employee discount program."
        res = score_job(jd, title="Card Inspector (Quality Assurance)", location="Atlantic City, NJ, us", country="US", company="Evolution", url="https://jobs.smartrecruiters.com/Evolution/744000144608239")
        self.assertTrue(res["is_disqualified"], f"Expected disqualified, got {res}")
        self.assertTrue(any("New Jersey" in r or "WA" in r for r in res["disqualified_by"]))

    def test_shield_ai_wichita(self):
        jd = "Staff Engineer, Quality Assurance (R5358) in Wichita Metro Area. Work on aircraft testing and flight certification."
        res = score_job(jd, title="Staff Engineer, Quality Assurance (R5358)", location="Wichita Metro Area", country="US", company="Shield AI", url="https://jobs.lever.co/shieldai/7f7e2632-717e-4684-a7a5-058e94360d81")
        self.assertTrue(res["is_disqualified"], f"Expected disqualified, got {res}")
        self.assertTrue(any("Kansas" in r or "WA" in r for r in res["disqualified_by"]))

    def test_builtin_dallas_title(self):
        jd = "SDET position at Photon in Dallas. Selenium, API Testing, Java, Karate Framework required."
        res = score_job(jd, title="SDET - Dallas, TX", location="", company="Photon", url="https://builtin.com/job/sdet-dallas-tx/10969711")
        self.assertTrue(res["is_disqualified"], f"Expected disqualified, got {res}")
        self.assertTrue(any("Texas" in r or "WA" in r for r in res["disqualified_by"]))

    def test_valid_issaquah_wa(self):
        jd = "Senior QA Engineer at UST in Issaquah, WA. Looking for Karate Framework, API Testing, Docker, AWS experience."
        res = score_job(jd, title="Senior QA Engineer", location="Issaquah, WA", country="United States", company="UST", url="https://www.linkedin.com/jobs/view/senior-qa-engineer-at-ust-4438780137")
        self.assertFalse(res["is_disqualified"], f"Expected qualified, got {res}")
        self.assertEqual(res["score_breakdown"]["signal"], 100)

    def test_valid_bothell_wa(self):
        jd = "Lead Quality Assurance at AT&T in Bothell, WA. API Testing, Regression Testing, Test Planning."
        res = score_job(jd, title="Lead Quality Assurance", location="Bothell, WA", country="United States", company="AT&T", url="https://www.linkedin.com/jobs/view/lead-quality-assurance-at-at-t-4466275139")
        self.assertFalse(res["is_disqualified"], f"Expected qualified, got {res}")
        self.assertEqual(res["score_breakdown"]["signal"], 100)

    def test_valid_us_remote(self):
        jd = "Senior QA Automation Engineer. 100% Remote - US candidates only. Experience with Karate Framework, Docker, AWS, Jira."
        res = score_job(jd, title="Senior QA Automation Engineer", location="Remote", country="United States", company="Acme Corp", url="https://boards.greenhouse.io/acme/jobs/123")
        self.assertFalse(res["is_disqualified"], f"Expected qualified, got {res}")
        self.assertEqual(res["score_breakdown"]["signal"], 85)

if __name__ == "__main__":
    unittest.main()
