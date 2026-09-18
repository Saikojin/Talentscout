import unittest
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.profile import get_user_location, create_profile, get_profile, delete_profile, default_config
from scripts.location_utils import evaluate_job_location, is_target_location, detect_us_state
from scripts.scorer import score_job

class TestProfileLocationSystem(unittest.TestCase):
    def test_default_user_location(self):
        loc = get_user_location()
        self.assertEqual(loc['country'], 'US')
        self.assertEqual(loc['city'], 'Redmond')
        self.assertIn('WA', loc['target_states'])
        self.assertTrue(loc['allow_remote'])
        self.assertTrue(loc['require_local_or_remote'])

    def test_wa_profile_evaluation(self):
        wa_cfg = get_user_location()
        # Local WA matches
        self.assertFalse(evaluate_job_location('Seattle, WA', 'US', profile_location=wa_cfg)['is_disqualified'])
        self.assertFalse(evaluate_job_location('Redmond, WA', 'US', profile_location=wa_cfg)['is_disqualified'])
        self.assertFalse(evaluate_job_location('Bellevue, WA', 'US', profile_location=wa_cfg)['is_disqualified'])
        
        # State disambiguation: Redmond, OR is Oregon, not WA
        eval_or = evaluate_job_location('Redmond, OR', 'US', profile_location=wa_cfg)
        self.assertTrue(eval_or['is_disqualified'])
        self.assertIn('Oregon', eval_or['reason'])

        # Foreign locations
        eval_my = evaluate_job_location('Kulim, Malaysia', 'MY', profile_location=wa_cfg)
        self.assertTrue(eval_my['is_disqualified'])

        # Other US States
        eval_tx = evaluate_job_location('Austin, TX', 'US', profile_location=wa_cfg)
        self.assertTrue(eval_tx['is_disqualified'])

        # US Remote
        eval_rem = evaluate_job_location('Remote - US', 'US', profile_location=wa_cfg)
        self.assertFalse(eval_rem['is_disqualified'])
        self.assertTrue(eval_rem['is_remote'])

    def test_tx_profile_evaluation(self):
        tx_cfg = {
            'country': 'US', 'state': 'Texas', 'city': 'Austin',
            'allowed_countries': ['US', 'USA'], 'target_states': ['TX', 'Texas'],
            'preferred_cities': ['Austin', 'Dallas'], 'allow_remote': True, 'require_local_or_remote': True
        }
        self.assertFalse(evaluate_job_location('Austin, TX', 'US', profile_location=tx_cfg)['is_disqualified'])
        self.assertFalse(evaluate_job_location('Dallas, TX', 'US', profile_location=tx_cfg)['is_disqualified'])
        self.assertTrue(evaluate_job_location('Seattle, WA', 'US', profile_location=tx_cfg)['is_disqualified'])
        self.assertTrue(evaluate_job_location('Redmond, OR', 'US', profile_location=tx_cfg)['is_disqualified'])

    def test_or_profile_evaluation(self):
        or_cfg = {
            'country': 'US', 'state': 'Oregon', 'city': 'Redmond',
            'allowed_countries': ['US', 'USA'], 'target_states': ['OR', 'Oregon'],
            'preferred_cities': ['Redmond', 'Portland'], 'allow_remote': True, 'require_local_or_remote': True
        }
        # Redmond, OR should PASS for an Oregon profile
        self.assertFalse(evaluate_job_location('Redmond, OR', 'US', profile_location=or_cfg)['is_disqualified'])
        self.assertFalse(evaluate_job_location('Portland, OR', 'US', profile_location=or_cfg)['is_disqualified'])
        self.assertTrue(evaluate_job_location('Seattle, WA', 'US', profile_location=or_cfg)['is_disqualified'])

    def test_scorer_integration(self):
        test_cfg = default_config()
        test_cfg['location']['target_states'] = ['TX', 'Texas']
        test_cfg['location']['preferred_cities'] = ['Austin']
        pid = create_profile('Test TX Profile', 'Testing TX Scoring', test_cfg)
        try:
            fetched = get_profile(pid)
            # Matching target state job
            res_match = score_job('Senior QA with Karate Framework, API Testing in Austin, TX', title='Senior QA Engineer', location='Austin, TX', country='US', profile_data=fetched)
            self.assertFalse(res_match['is_disqualified'])
            self.assertEqual(res_match['score_breakdown']['signal'], 100)

            # Non-target state job
            res_non_match = score_job('Senior QA with Karate Framework in Seattle, WA', title='Senior QA Engineer', location='Seattle, WA', country='US', profile_data=fetched)
            self.assertTrue(res_non_match['is_disqualified'])
            self.assertIn('SafetyNet: Not remote and not in TX (Washington)', res_non_match['disqualified_by'])
        finally:
            delete_profile(pid)

    def test_empty_jd_disqualification(self):
        # Empty description (<50 chars)
        res_empty = score_job("", title="Senior Quality Engineer", location="Seattle, WA", country="US")
        self.assertTrue(res_empty['is_disqualified'])
        self.assertIn("SafetyNet: Empty or invalid job description", res_empty['disqualified_by'])
        self.assertLessEqual(res_empty['score'], 26)

        # Non-empty description (>=50 chars) with skills
        jd_valid = "We are seeking a Senior QA Engineer with Karate Framework, Docker, AWS, Jira, and API Testing experience in Seattle."
        res_valid = score_job(jd_valid, title="Senior QA Engineer", location="Seattle, WA", country="US")
        self.assertFalse(res_valid['is_disqualified'])
        self.assertGreater(res_valid['score'], 50)

    def test_foreign_url_and_company_detection(self):
        # Test case matching Jungheinrich Croatia leak from LinkedIn
        url_hr = "https://hr.linkedin.com/jobs/view/robot-software-quality-assurance-team-lead-at-jungheinrich-croatia-4452803297"
        res_hr = score_job(
            "Lead QA Automation engineer with Python, Robot Framework, and CI/CD experience.",
            title="Robot Software Quality Assurance Team Lead",
            location="Remote",
            company="Jungheinrich Croatia",
            url=url_hr
        )
        self.assertTrue(res_hr['is_disqualified'])
        self.assertTrue(any("Croatia" in reason for reason in res_hr['disqualified_by']))

        # Test foreign company name
        res_comp = score_job(
            "QA Engineer working on embedded systems and automation test framework.",
            title="QA Engineer",
            location="Remote",
            company="Renesas Malaysia",
            url="https://www.linkedin.com/jobs/view/9999"
        )
        self.assertTrue(res_comp['is_disqualified'])
        self.assertTrue(any("Malaysia" in reason for reason in res_comp['disqualified_by']))

    def test_non_job_url_filtering(self):
        from scripts.auto_scour import is_non_job_url
        self.assertTrue(is_non_job_url("https://careers.cencora.com/us/en/c/quality-jobs"))
        self.assertTrue(is_non_job_url("https://company.com/jobcart"))
        self.assertTrue(is_non_job_url("https://company.com/locations"))
        self.assertTrue(is_non_job_url("https://company.com/early-careers"))
        self.assertFalse(is_non_job_url("https://careers.cencora.com/us/en/job/R12345/senior-quality-engineer"))
        self.assertFalse(is_non_job_url("https://www.linkedin.com/jobs/view/123456789"))

if __name__ == '__main__':
    unittest.main()
