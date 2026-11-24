import json
import os
import sys
import zipfile
from unittest.mock import MagicMock, patch

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import scripts.database as db_mod
import scripts.profile as profile_mod
from scripts.auto_scour import parse_args
from scripts.ci_bootstrap import mask_email
from scripts.import_package import import_package
from scripts.package_and_email import (
    build_digest_email,
    build_profile_package,
    run_packaging_and_delivery,
)


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    """Point TalentScout SQLite to an isolated temp database for each test."""
    test_db = str(tmp_path / "test_job_tracker.db")
    monkeypatch.setattr(db_mod, "DB_PATH", test_db)
    profile_mod.invalidate_cache()
    db_mod.init_db()
    profile_mod.seed_default_profile()
    yield test_db
    profile_mod.invalidate_cache()


def test_delivery_config_validation_and_masking():
    cfg = profile_mod.validate_config({
        "delivery": {
            "enabled": True,
            "recipient_email": "  alice@example.com  ",
            "min_score": 150,
            "max_jobs": 0,
            "include_formats": ["JSON", "invalid", "md"],
        }
    })
    assert cfg["delivery"]["enabled"] is True
    assert cfg["delivery"]["recipient_email"] == "alice@example.com"
    assert cfg["delivery"]["min_score"] == 100
    assert cfg["delivery"]["max_jobs"] == 1
    assert cfg["delivery"]["include_formats"] == ["json", "md"]

    assert mask_email("thomas.snyder@example.com") == "t***@example.com"
    assert mask_email("") == "(none)"


def test_sync_profiles_from_env_single_and_multi(isolated_db, monkeypatch):
    # Single-user shortcut via RECIPIENT_EMAIL
    monkeypatch.delenv("TALENTSCOUT_PROFILES_JSON", raising=False)
    monkeypatch.setenv("RECIPIENT_EMAIL", "solo@example.com")
    monkeypatch.setenv("DELIVERY_MIN_SCORE", "55")
    monkeypatch.setenv("DELIVERY_MAX_JOBS", "25")

    synced = profile_mod.sync_profiles_from_env()
    assert len(synced) == 1
    enabled = profile_mod.get_delivery_enabled_profiles()
    assert len(enabled) == 1
    assert enabled[0]["config"]["delivery"]["recipient_email"] == "solo@example.com"
    assert enabled[0]["config"]["delivery"]["min_score"] == 55
    assert enabled[0]["config"]["delivery"]["max_jobs"] == 25

    # Multi-profile JSON sync (idempotent upsert)
    multi = [
        {
            "name": "Default Profile",
            "recipient_email": "primary@example.com",
            "delivery": {"enabled": True, "min_score": 45, "max_jobs": 40},
        },
        {
            "name": "Backend Friend",
            "recipient_email": "friend@example.com",
            "delivery": {"enabled": True, "min_score": 60, "max_jobs": 20},
            "search": {"default_terms": ["Go Developer"]},
        },
    ]
    monkeypatch.setenv("TALENTSCOUT_PROFILES_JSON", json.dumps(multi))
    monkeypatch.delenv("RECIPIENT_EMAIL", raising=False)

    profile_mod.sync_profiles_from_env()
    # Second sync must be idempotent (still 2 profiles, no duplicates)
    profile_mod.sync_profiles_from_env()
    enabled_multi = profile_mod.get_delivery_enabled_profiles()
    names = {p["name"]: p["config"]["delivery"]["recipient_email"] for p in enabled_multi}
    assert names == {
        "Default Profile": "primary@example.com",
        "Backend Friend": "friend@example.com",
    }


def test_package_roundtrip_and_idempotent_import(isolated_db, tmp_path, monkeypatch):
    active = profile_mod.get_active_profile()
    pid = active["id"]

    j1 = db_mod.add_job(
        title="Staff SDET",
        company="Acme Corp",
        url="https://jobs.example.com/1",
        site_source="Greenhouse",
        score=88,
        missing_skills=["Rust"],
        matched_skills=["Karate Framework", "Kubernetes", "Docker"],
        score_profile_id=pid,
        location="Seattle, WA",
        country="US",
        description="Lead QA automation across microservices.",
    )
    j2 = db_mod.add_job(
        title="Low Match Intern",
        company="Noise LLC",
        url="https://jobs.example.com/2",
        site_source="Lever",
        score=20,
        missing_skills=["Everything"],
        matched_skills=[],
        score_profile_id=pid,
        location="Remote",
        country="US",
    )
    assert j1 is not None and j2 is not None

    telemetry_file = tmp_path / "scour_summary_latest.json"
    telemetry_file.write_text(json.dumps({"discovered": 2, "passed": 1}), encoding="utf-8")

    jobs = db_mod.get_undelivered_jobs_for_profile(pid, min_score=40, limit=50)
    assert len(jobs) == 1
    assert jobs[0]["title"] == "Staff SDET"

    pkg_dir = str(tmp_path / "packages")
    zip_path, manifest = build_profile_package(
        profile=active,
        jobs=jobs,
        run_id="test-run-42",
        out_dir=pkg_dir,
        telemetry_path=str(telemetry_file),
    )
    assert os.path.exists(zip_path)
    assert manifest["job_count"] == 1
    assert manifest["descriptions_included"] is True

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
        assert {"manifest.json", "jobs_delta.json", "jobs_summary.csv", "jobs_digest.md", "scour_telemetry.json"}.issubset(names)
        delta = json.loads(zf.read("jobs_delta.json").decode("utf-8"))
        assert delta["jobs"][0]["description"] == "Lead QA automation across microservices."

    # Import package into a brand-new local SQLite database
    local_db = str(tmp_path / "local_target.db")
    monkeypatch.setattr(db_mod, "DB_PATH", local_db)
    profile_mod.invalidate_cache()
    db_mod.init_db()
    profile_mod.seed_default_profile()

    first_import = import_package(zip_path)
    assert first_import["imported"] == 1
    assert first_import["skipped_existing_or_invalid"] == 0

    second_import = import_package(zip_path)
    assert second_import["imported"] == 0
    assert second_import["skipped_existing_or_invalid"] == 1

    stored = db_mod.get_new_jobs()
    assert len(stored) == 1
    assert stored[0]["title"] == "Staff SDET"
    assert stored[0]["description"] == "Lead QA automation across microservices."


def test_smtp_delivery_delta_and_failure_safety(isolated_db, tmp_path, monkeypatch):
    monkeypatch.delenv("TALENTSCOUT_PROFILES_JSON", raising=False)
    monkeypatch.setenv("RECIPIENT_EMAIL", "candidate@example.com")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "sender@example.com")
    monkeypatch.setenv("SMTP_PASS", "app-secret")
    monkeypatch.setenv("SMTP_SECURITY", "starttls")

    profile_mod.sync_profiles_from_env()
    active = profile_mod.get_active_profile()

    db_mod.add_job(
        title="Principal QA Architect",
        company="CloudScale",
        url="https://jobs.example.com/99",
        site_source="Ashby",
        score=92,
        matched_skills=["SDET", "AWS"],
        missing_skills=[],
        score_profile_id=active["id"],
        location="Remote (US)",
        country="US",
    )

    out_dir = str(tmp_path / "out")

    # 1. Dry-run builds package without sending or marking delivered
    dry_res = run_packaging_and_delivery(run_id="run-dry", out_dir=out_dir, dry_run=True)
    assert dry_res[0]["status"] == "dry_run"
    assert dry_res[0]["emailed"] is False
    assert db_mod.get_profile_delivery_stats(active["id"])["delivered_count"] == 0

    # 2. Failed SMTP must NOT mark job as delivered (retries safely next run)
    with patch("scripts.package_and_email.smtplib.SMTP", side_effect=OSError("SMTP unreachable")):
        with pytest.raises(OSError):
            run_packaging_and_delivery(run_id="run-fail", out_dir=out_dir)
    assert db_mod.get_profile_delivery_stats(active["id"])["delivered_count"] == 0

    # 3. Successful SMTP delivers attachment + records delivery
    sent_messages = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=30):
            self.host = host
            self.port = port

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def ehlo(self):
            pass

        def ehlo_or_helo_if_needed(self):
            pass

        def has_extn(self, name):
            return False

        def starttls(self, context=None):
            pass

        def login(self, user, pwd):
            assert user == "sender@example.com"
            assert pwd == "app-secret"

        def send_message(self, msg):
            sent_messages.append(msg)

    with patch("scripts.package_and_email.smtplib.SMTP", FakeSMTP):
        ok_res = run_packaging_and_delivery(run_id="run-ok-1", out_dir=out_dir)
    assert ok_res[0]["status"] == "delivered"
    assert ok_res[0]["emailed"] is True
    assert ok_res[0]["recorded_deliveries"] == 1
    assert len(sent_messages) == 1
    attachments = list(sent_messages[0].iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename().endswith(".zip")

    # 4. Subsequent run sees 0 new jobs and skips email completely
    with patch("scripts.package_and_email.smtplib.SMTP", FakeSMTP):
        next_res = run_packaging_and_delivery(run_id="run-ok-2", out_dir=out_dir)
    assert next_res[0]["status"] == "skipped"
    assert next_res[0]["job_count"] == 0
    assert len(sent_messages) == 1


def test_auto_scour_ci_cli_args():
    parsed = parse_args(["--mode", "fast", "--profile", "Default Profile", "--time-budget", "20", "--max-companies", "100", "--dry-run"])
    assert parsed.mode == "fast"
    assert parsed.profile == "Default Profile"
    assert parsed.time_budget == 20.0
    assert parsed.max_companies == 100
    assert parsed.dry_run is True


def test_smtp_surfaces_gmail_535_instead_of_disconnect():
    """Reproduce Gmail closing the socket after 535 on AUTH PLAIN so 535 is never masked."""
    import smtplib
    from scripts.package_and_email import _smtp_authenticate

    class GmailLikeSMTP:
        esmtp_features = {"auth": "LOGIN PLAIN XOAUTH2"}
        user = None
        password = None

        def ehlo_or_helo_if_needed(self):
            pass

        def has_extn(self, name):
            return name == "auth"

        def auth_plain(self, challenge=None):
            return f"\0{self.user}\0{self.password}"

        def auth_login(self, challenge=None):
            return self.user

        def auth(self, method, handler, initial_response_ok=True):
            if method == "PLAIN":
                raise smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")
            # Gmail drops the socket after 535, so a second attempt would disconnect
            raise smtplib.SMTPServerDisconnected("Connection unexpectedly closed")

    with pytest.raises(smtplib.SMTPAuthenticationError) as exc_info:
        _smtp_authenticate(GmailLikeSMTP(), "user@gmail.com", "wrong-or-non-app-pass")
    assert exc_info.value.smtp_code == 535


def test_canonicalize_job_url_strips_tracking_preserves_job_ids():
    li_morning = (
        "https://www.linkedin.com/jobs/view/agentic-qa-developer-at-fractal-4483812329"
        "?position=13&pageNum=0&refId=P0Ts6EZFRTCmzVWR%2BAr5pg%3D%3D&trackingId=abHzzVH8Nx4jsq8%2BrxJEzA%3D%3D"
    )
    li_afternoon = (
        "https://www.linkedin.com/jobs/view/agentic-qa-developer-at-fractal-4483812329"
        "?position=8&pageNum=0&refId=OvzF22bdQa5wMOnSfcgecw%3D%3D&trackingId=athzHAAGLYwTaG6rvrlATg%3D%3D"
    )
    assert db_mod.canonicalize_job_url(li_morning) == "https://www.linkedin.com/jobs/view/agentic-qa-developer-at-fractal-4483812329"
    assert db_mod.canonicalize_job_url(li_morning) == db_mod.canonicalize_job_url(li_afternoon)

    # Meaningful ID query parameters must be preserved while utm_* / gh_src are stripped
    indeed = "http://www.indeed.com/viewjob?jk=abc123&utm_source=email&ref=foo#apply"
    assert db_mod.canonicalize_job_url(indeed) == "https://www.indeed.com/viewjob?jk=abc123"
    gh = "https://boards.greenhouse.io/acme/jobs?gh_jid=98765&gh_src=abcd"
    assert db_mod.canonicalize_job_url(gh) == "https://boards.greenhouse.io/acme/jobs?gh_jid=98765"


def test_dedup_across_rotated_linkedin_urls_delivery_and_import(isolated_db, tmp_path):
    active = profile_mod.get_active_profile()
    pid = active["id"]

    url_run1 = (
        "https://www.linkedin.com/jobs/view/agentic-qa-developer-at-fractal-4483812329"
        "?position=13&pageNum=0&refId=AAA&trackingId=111"
    )
    url_run2 = (
        "https://www.linkedin.com/jobs/view/agentic-qa-developer-at-fractal-4483812329"
        "?position=5&pageNum=0&refId=BBB&trackingId=222"
    )

    # Insert from Run 1 (status='new') — canonicalized automatically
    jid1 = db_mod.add_job(
        title="Agentic QA Developer",
        company="Fractal",
        url=url_run1,
        site_source="LinkedIn",
        score=62,
        score_profile_id=pid,
    )
    assert jid1 is not None

    # Even while status='new', rotated URL or same (title, company) must be treated as duplicate
    assert db_mod.is_duplicate(url_run2, "Agentic QA Developer", "Fractal") is True
    assert db_mod.add_job(
        title="Agentic QA Developer",
        company="Fractal",
        url=url_run2,
        site_source="LinkedIn",
        score=62,
        score_profile_id=pid,
    ) is None

    # Simulate legacy cached DB row inserted before canonicalization existed + already delivered
    conn = db_mod.create_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO jobs (title, company, url, site_source, status, date_added, score, score_profile_id) "
        "VALUES (?, ?, ?, ?, 'new', '2026-11-23T17:00:00', 60, ?)",
        ("Senior Quality Engineer", "Paradigm", url_run1 + "_legacy", "LinkedIn", pid),
    )
    legacy_id = cur.lastrowid
    cur.execute(
        "INSERT INTO jobs (title, company, url, site_source, status, date_added, score, score_profile_id) "
        "VALUES (?, ?, ?, ?, 'new', '2026-11-23T23:00:00', 60, ?)",
        ("Senior Quality Engineer", "Paradigm", url_run2 + "_legacy2", "LinkedIn", pid),
    )
    conn.commit()
    conn.close()

    db_mod.record_profile_deliveries(pid, [jid1, legacy_id], "run-morning")
    undelivered = db_mod.get_undelivered_jobs_for_profile(pid, min_score=40, limit=50)
    assert undelivered == []

    # Import package containing 1 rotated LinkedIn duplicate + 1 genuinely new role
    pkg_json = tmp_path / "jobs_delta.json"
    pkg_json.write_text(
        json.dumps({
            "run_id": "run-afternoon",
            "jobs": [
                {"title": "Agentic QA Developer", "company": "Fractal", "url": url_run2, "score": 62},
                {"title": "Automation Engineer", "company": "ALTEN Technology USA", "url": "https://job-boards.greenhouse.io/altentechnologyusa/jobs/5174154007", "score": 48},
            ],
        }),
        encoding="utf-8",
    )

    dry = import_package(str(pkg_json), dry_run=True)
    assert dry["imported"] == 1
    assert dry["skipped_duplicate"] == 1

    real = import_package(str(pkg_json), dry_run=False)
    assert real["imported"] == 1
    assert real["skipped_duplicate"] == 1

    # Re-running import is 100% idempotent
    again = import_package(str(pkg_json), dry_run=False)
    assert again["imported"] == 0
    assert again["skipped_duplicate"] == 2


