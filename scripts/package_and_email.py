"""
Package newly discovered jobs per profile into portable .zip archives and deliver them
via SMTP email (stdlib smtplib + email.message.EmailMessage, zero extra dependencies).

Security / Public-Repo Hygiene:
  - Never prints SMTP passwords or unmasked recipient email addresses to stdout.
  - All credentials and optional private profile configs come from environment variables
    (e.g. GitHub Actions Secrets, GitLab CI Variables, local .env).
  - Delivery tracking in SQLite `profile_deliveries` is updated ONLY after SMTP delivery
    succeeds (idempotent on retries).
"""
import argparse
import csv
import datetime
import html
import io
import json
import os
import re
import smtplib
import ssl
import sys
import zipfile
from email.message import EmailMessage
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from scripts.ci_bootstrap import mask_email
from scripts.database import (
    get_profile_delivery_stats,
    get_undelivered_jobs_for_profile,
    record_profile_deliveries,
)
from scripts.profile import (
    get_active_profile,
    get_delivery_enabled_profiles,
    get_profile,
    get_profile_by_name,
    sync_profiles_from_env,
)

PACKAGE_SCHEMA_VERSION = 1
MAX_ATTACHMENT_BYTES = 18 * 1024 * 1024  # Safe ceiling under 25 MB SMTP limits


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "profile").strip().lower()).strip("-")
    return slug or "profile"


def _parse_json_list(raw: Any) -> List[str]:
    if isinstance(raw, list):
        return [str(x) for x in raw if x is not None]
    if isinstance(raw, str) and raw.strip():
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, list):
                return [str(x) for x in decoded if x is not None]
        except json.JSONDecodeError:
            return [s.strip() for s in raw.split(",") if s.strip()]
    return []


def _normalize_job_for_export(job: dict, include_description: bool = True) -> dict:
    return {
        "id": job.get("id"),
        "title": job.get("title") or "",
        "company": job.get("company") or "",
        "url": job.get("url") or "",
        "site_source": job.get("site_source") or "",
        "score": job.get("score") if job.get("score") is not None else 0,
        "location": job.get("location") or "",
        "country": job.get("country") or "",
        "matched_skills": _parse_json_list(job.get("matched_skills")),
        "missing_skills": _parse_json_list(job.get("missing_skills")),
        "date_added": job.get("date_added") or "",
        "description": (job.get("description") or "") if include_description else "",
    }


def _render_csv(jobs: List[dict]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "score",
        "title",
        "company",
        "location",
        "country",
        "site_source",
        "matched_skills",
        "missing_skills",
        "date_added",
        "url",
    ])
    for job in jobs:
        writer.writerow([
            job["score"],
            job["title"],
            job["company"],
            job["location"],
            job["country"],
            job["site_source"],
            ", ".join(job["matched_skills"]),
            ", ".join(job["missing_skills"]),
            job["date_added"],
            job["url"],
        ])
    return buf.getvalue()


def _render_markdown(profile_name: str, run_id: str, generated_at: str, jobs: List[dict]) -> str:
    lines = [
        f"# TalentScout Digest — {profile_name}",
        "",
        f"- **Run ID:** `{run_id}`",
        f"- **Generated (UTC):** `{generated_at}`",
        f"- **New Jobs Packaged:** {len(jobs)}",
        "",
        "| Score | Role | Company | Location | Matched Skills | Missing Skills | Link |",
        "| ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for job in jobs:
        title = job["title"].replace("|", "/")
        company = job["company"].replace("|", "/")
        location = (job["location"] or job["country"] or "Unspecified").replace("|", "/")
        matched = ", ".join(job["matched_skills"][:5]).replace("|", "/") or "-"
        missing = ", ".join(job["missing_skills"][:3]).replace("|", "/") or "None"
        url = job["url"]
        lines.append(f"| {job['score']} | {title} | {company} | {location} | {matched} | {missing} | [Apply]({url}) |")
    lines.append("")
    return "\n".join(lines)


def _load_telemetry_if_present(telemetry_path: Optional[str]) -> Optional[dict]:
    if not telemetry_path or not os.path.exists(telemetry_path):
        return None
    try:
        with open(telemetry_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def build_profile_package(
    profile: dict,
    jobs: List[dict],
    run_id: str,
    out_dir: str,
    telemetry_path: Optional[str] = None,
) -> Tuple[str, dict]:
    """
    Build a portable .zip data package for a profile's newly discovered jobs.
    Returns (zip_path, manifest_dict).
    """
    os.makedirs(out_dir, exist_ok=True)
    generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ts_compact = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    profile_name = profile.get("name", "Default Profile")
    deliv_cfg = profile.get("config", {}).get("delivery", {})
    formats = set(deliv_cfg.get("include_formats", ["json", "csv", "md"]))

    telemetry_data = _load_telemetry_if_present(telemetry_path)
    zip_filename = f"talentscout_{_slugify(profile_name)}_{ts_compact}.zip"
    zip_path = os.path.join(out_dir, zip_filename)

    def _write_zip(include_descriptions: bool) -> dict:
        export_jobs = [_normalize_job_for_export(j, include_description=include_descriptions) for j in jobs]
        manifest = {
            "schema_version": PACKAGE_SCHEMA_VERSION,
            "run_id": run_id,
            "generated_at_utc": generated_at,
            "profile_name": profile_name,
            "job_count": len(export_jobs),
            "min_score": deliv_cfg.get("min_score", 40),
            "descriptions_included": include_descriptions,
            "files": ["manifest.json"],
        }

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            if "json" in formats:
                payload = {
                    "schema_version": PACKAGE_SCHEMA_VERSION,
                    "run_id": run_id,
                    "generated_at_utc": generated_at,
                    "profile_name": profile_name,
                    "jobs": export_jobs,
                }
                zf.writestr("jobs_delta.json", json.dumps(payload, indent=2, ensure_ascii=False))
                manifest["files"].append("jobs_delta.json")

            if "csv" in formats:
                zf.writestr("jobs_summary.csv", _render_csv(export_jobs))
                manifest["files"].append("jobs_summary.csv")

            if "md" in formats:
                zf.writestr("jobs_digest.md", _render_markdown(profile_name, run_id, generated_at, export_jobs))
                manifest["files"].append("jobs_digest.md")

            if telemetry_data is not None:
                zf.writestr("scour_telemetry.json", json.dumps(telemetry_data, indent=2))
                manifest["files"].append("scour_telemetry.json")

            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

        return manifest

    manifest = _write_zip(include_descriptions=True)
    if os.path.getsize(zip_path) > MAX_ATTACHMENT_BYTES:
        manifest = _write_zip(include_descriptions=False)
        manifest["trimmed_for_email_limit"] = True

    manifest["package_bytes"] = os.path.getsize(zip_path)
    manifest["package_filename"] = zip_filename
    return zip_path, manifest


def build_digest_email(
    profile: dict,
    jobs: List[dict],
    zip_path: str,
    manifest: dict,
    sender_email: str,
    recipient_email: str,
) -> EmailMessage:
    """Build a multipart plain+HTML email with the profile's .zip package attached."""
    profile_name = profile.get("name", "Default Profile")
    export_jobs = [_normalize_job_for_export(j, include_description=False) for j in jobs]
    top_score = max((j["score"] for j in export_jobs), default=0)
    run_id = manifest.get("run_id", "manual")
    date_label = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    msg = EmailMessage()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    if export_jobs:
        msg["Subject"] = f"[TalentScout] {len(export_jobs)} new roles for {profile_name} (Top score: {top_score})"
    else:
        msg["Subject"] = f"[TalentScout] 0 new roles for {profile_name} ({date_label})"

    # Plain-text body
    plain_lines = [
        f"TalentScout Scheduled Digest — {profile_name}",
        f"Run ID: {run_id} | Generated: {date_label}",
        f"New roles packaged: {len(export_jobs)}",
        "",
    ]
    for job in export_jobs[:15]:
        loc = job["location"] or job["country"] or "Unspecified"
        plain_lines.append(f"- [{job['score']}] {job['title']} @ {job['company']} ({loc})")
        plain_lines.append(f"  {job['url']}")
    if len(export_jobs) > 15:
        plain_lines.append(f"\n...and {len(export_jobs) - 15} more inside the attached ZIP package.")
    plain_lines.extend([
        "",
        f"Attached package: {os.path.basename(zip_path)}",
        "Import into local TalentScout:",
        f"  python scripts/import_package.py {os.path.basename(zip_path)}",
    ])
    msg.set_content("\n".join(plain_lines))

    # HTML body
    rows_html = []
    for job in export_jobs[:20]:
        score = int(job["score"])
        badge_bg = "#1f6feb" if score >= 75 else ("#238636" if score >= 55 else "#6e7681")
        matched = ", ".join(job["matched_skills"][:4]) or "-"
        loc = job["location"] or job["country"] or "Unspecified"
        rows_html.append(
            "<tr>"
            f"<td style='padding:8px;border-bottom:1px solid #30363d;text-align:center;'>"
            f"<span style='display:inline-block;padding:2px 8px;border-radius:12px;background:{badge_bg};color:#fff;font-weight:700;font-size:12px;'>{score}</span>"
            "</td>"
            f"<td style='padding:8px;border-bottom:1px solid #30363d;'>"
            f"<a href='{html.escape(job['url'], quote=True)}' style='color:#58a6ff;font-weight:600;text-decoration:none;'>{html.escape(job['title'])}</a>"
            f"<div style='color:#8b949e;font-size:12px;'>{html.escape(job['company'])} · {html.escape(loc)}</div>"
            "</td>"
            f"<td style='padding:8px;border-bottom:1px solid #30363d;color:#c9d1d9;font-size:12px;'>{html.escape(matched)}</td>"
            "</tr>"
        )

    table_block = (
        "<table style='width:100%;border-collapse:collapse;margin-top:12px;'>"
        "<thead><tr>"
        "<th style='text-align:center;padding:8px;border-bottom:2px solid #30363d;color:#8b949e;font-size:12px;'>Score</th>"
        "<th style='text-align:left;padding:8px;border-bottom:2px solid #30363d;color:#8b949e;font-size:12px;'>Role & Company</th>"
        "<th style='text-align:left;padding:8px;border-bottom:2px solid #30363d;color:#8b949e;font-size:12px;'>Matched Skills</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody></table>"
        if rows_html
        else "<p style='color:#8b949e;'>No new qualifying roles matched this run window.</p>"
    )

    html_body = f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:20px;background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">
  <div style="max-width:720px;margin:0 auto;background:#161b22;border:1px solid #30363d;border-radius:10px;padding:24px;">
    <h2 style="margin:0 0 6px;color:#58a6ff;">TalentScout Scheduled Digest</h2>
    <p style="margin:0 0 16px;color:#8b949e;font-size:13px;">
      Profile: <strong style="color:#e6edf3;">{html.escape(profile_name)}</strong> ·
      New roles: <strong style="color:#e6edf3;">{len(export_jobs)}</strong> ·
      Run: <code>{html.escape(str(run_id))}</code>
    </p>
    {table_block}
    <div style="margin-top:20px;padding:12px;background:#0d1117;border:1px solid #30363d;border-radius:6px;font-size:12px;color:#8b949e;">
      <div><strong style="color:#e6edf3;">Attached Package:</strong> <code>{html.escape(os.path.basename(zip_path))}</code> ({manifest.get('package_bytes', 0):,} bytes)</div>
      <div style="margin-top:6px;">Import locally into SQLite: <code>python scripts/import_package.py {html.escape(os.path.basename(zip_path))}</code></div>
    </div>
  </div>
</body>
</html>"""
    msg.add_alternative(html_body, subtype="html")

    with open(zip_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="zip",
            filename=os.path.basename(zip_path),
        )

    return msg


def load_smtp_config_from_env() -> dict:
    host = os.environ.get("SMTP_HOST", "").strip()
    port_raw = os.environ.get("SMTP_PORT", "587").strip() or "587"
    port = int(port_raw)
    username = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASS", "").strip()
    sender = os.environ.get("SMTP_FROM", "").strip() or username
    security = os.environ.get("SMTP_SECURITY", "").strip().lower()
    if security not in ("starttls", "ssl", "none"):
        security = "ssl" if port == 465 else "starttls"

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "sender": sender,
        "security": security,
    }


def _smtp_authenticate(server: smtplib.SMTP, username: str, password: str) -> None:
    """
    Authenticate against an SMTP server without letting smtplib.SMTP.login() mask
    a real 534/535 SMTPAuthenticationError behind SMTPServerDisconnected when the
    server (notably Gmail) closes the socket immediately after rejecting AUTH PLAIN.
    """
    server.ehlo_or_helo_if_needed()
    if not server.has_extn("auth"):
        # Fallback for stub/mock servers in unit tests that implement login() directly
        server.login(username, password)
        return

    advertised = server.esmtp_features.get("auth", "").split()
    authlist = [m for m in ("CRAM-MD5", "PLAIN", "LOGIN") if m in advertised]
    if not authlist:
        raise smtplib.SMTPException(f"No supported SMTP AUTH mechanism advertised ({advertised}).")

    server.user, server.password = username, password
    last_auth_error: Optional[smtplib.SMTPAuthenticationError] = None

    for method in authlist:
        handler = getattr(server, "auth_" + method.lower().replace("-", "_"))
        try:
            code, resp = server.auth(method, handler, initial_response_ok=True)
            if code in (235, 503):
                return
        except smtplib.SMTPAuthenticationError as exc:
            last_auth_error = exc
            # Definitive credential / policy rejections (534, 535) should surface immediately;
            # Gmail drops the TCP socket right after 535 so retrying LOGIN causes a misleading disconnect.
            if exc.smtp_code in (534, 535):
                raise
        except smtplib.SMTPServerDisconnected:
            if last_auth_error is not None:
                raise last_auth_error
            raise

    if last_auth_error is not None:
        raise last_auth_error


def send_email_smtp(msg: EmailMessage, smtp_cfg: dict, timeout: int = 30) -> None:
    """Deliver EmailMessage via SMTP (STARTTLS, SSL, or plain for local test servers)."""
    host = smtp_cfg.get("host")
    port = int(smtp_cfg.get("port", 587))
    security = smtp_cfg.get("security", "starttls")
    username = smtp_cfg.get("username", "")
    password = smtp_cfg.get("password", "")

    if not host:
        raise ValueError("SMTP_HOST is required to send email.")

    print(
        f"[*] Connecting to SMTP {host}:{port} "
        f"(security={security}, user={mask_email(username)})..."
    )

    context = ssl.create_default_context()
    try:
        if security == "ssl":
            with smtplib.SMTP_SSL(host, port, timeout=timeout, context=context) as server:
                if username and password:
                    _smtp_authenticate(server, username, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as server:
                server.ehlo()
                if security == "starttls":
                    server.starttls(context=context)
                    server.ehlo()
                if username and password:
                    _smtp_authenticate(server, username, password)
                server.send_message(msg)
    except smtplib.SMTPAuthenticationError as exc:
        detail = exc.smtp_error.decode("utf-8", errors="replace") if isinstance(exc.smtp_error, bytes) else str(exc.smtp_error)
        print(f"[!] SMTP authentication rejected ({exc.smtp_code}): {detail}")
        if "gmail.com" in host.lower():
            print(
                "[!] Gmail hint: Verify SMTP_USER is your full '@gmail.com' address and SMTP_PASS is a "
                "16-character Google App Password (from https://myaccount.google.com/apppasswords, "
                "not your regular Gmail login password)."
            )
        raise


def _resolve_target_profiles(profile_arg: Optional[str]) -> List[dict]:
    if profile_arg:
        if profile_arg.isdigit():
            prof = get_profile(int(profile_arg))
        else:
            prof = get_profile_by_name(profile_arg)
        if not prof:
            raise ValueError(f"Profile '{profile_arg}' not found.")
        return [prof]

    enabled = get_delivery_enabled_profiles()
    if enabled:
        return enabled

    # Fallback in dry-run / local package mode: use active profile
    return [get_active_profile()]


def run_packaging_and_delivery(
    profile_arg: Optional[str] = None,
    run_id: Optional[str] = None,
    out_dir: str = "logs/packages",
    telemetry_path: str = "logs/scour_summary_latest.json",
    sync_env: bool = True,
    dry_run: bool = False,
    skip_email: bool = False,
) -> List[dict]:
    """Orchestrate packaging and SMTP delivery across one or all delivery-enabled profiles."""
    if sync_env:
        sync_profiles_from_env()

    resolved_run_id = (
        run_id
        or os.environ.get("GITHUB_RUN_ID")
        or datetime.datetime.now(datetime.timezone.utc).strftime("local_%Y%m%d_%H%M%S")
    )
    profiles = _resolve_target_profiles(profile_arg)
    smtp_cfg = load_smtp_config_from_env()
    results: List[dict] = []

    for prof in profiles:
        pid = prof["id"]
        pname = prof["name"]
        deliv_cfg = prof.get("config", {}).get("delivery", {})
        recipient = deliv_cfg.get("recipient_email", "").strip()
        min_score = int(deliv_cfg.get("min_score", 40))
        max_jobs = int(deliv_cfg.get("max_jobs", 50))
        send_empty = bool(deliv_cfg.get("send_empty_digest", False))

        jobs = get_undelivered_jobs_for_profile(
            profile_id=pid,
            min_score=min_score,
            limit=max_jobs,
            include_unscoped=True,
        )

        entry = {
            "profile_id": pid,
            "profile_name": pname,
            "recipient_masked": mask_email(recipient),
            "job_count": len(jobs),
            "package_path": None,
            "emailed": False,
            "recorded_deliveries": 0,
            "status": "skipped",
        }

        if not jobs and not send_empty:
            print(f"[*] Profile '{pname}': 0 new qualifying jobs (min_score={min_score}). Skipping package/email.")
            results.append(entry)
            continue

        zip_path, manifest = build_profile_package(
            profile=prof,
            jobs=jobs,
            run_id=resolved_run_id,
            out_dir=out_dir,
            telemetry_path=telemetry_path,
        )
        entry["package_path"] = zip_path
        entry["package_bytes"] = manifest["package_bytes"]

        if dry_run or skip_email:
            entry["status"] = "dry_run" if dry_run else "packaged_only"
            print(
                f"[*] [{entry['status'].upper()}] Profile '{pname}': packaged {len(jobs)} jobs -> {zip_path} "
                f"(recipient: {mask_email(recipient)})"
            )
            results.append(entry)
            continue

        if not recipient:
            entry["status"] = "no_recipient"
            print(f"[!] Profile '{pname}': recipient_email is empty. Package saved to {zip_path}, email skipped.")
            results.append(entry)
            continue

        if not smtp_cfg["host"] or not smtp_cfg["sender"]:
            entry["status"] = "smtp_unconfigured"
            print(
                f"[!] Profile '{pname}': SMTP_HOST/SMTP_FROM not configured. "
                f"Package saved to {zip_path}, email skipped."
            )
            results.append(entry)
            continue

        msg = build_digest_email(
            profile=prof,
            jobs=jobs,
            zip_path=zip_path,
            manifest=manifest,
            sender_email=smtp_cfg["sender"],
            recipient_email=recipient,
        )
        send_email_smtp(msg, smtp_cfg)
        entry["emailed"] = True
        recorded = record_profile_deliveries(pid, [j["id"] for j in jobs if j.get("id") is not None], resolved_run_id)
        entry["recorded_deliveries"] = recorded
        entry["status"] = "delivered"

        stats = get_profile_delivery_stats(pid)
        print(
            f"[+] Delivered {len(jobs)} jobs to {mask_email(recipient)} for profile '{pname}' "
            f"(package: {os.path.basename(zip_path)}, cumulative delivered: {stats['delivered_count']})."
        )
        results.append(entry)

    return results


def main(args=None):
    parser = argparse.ArgumentParser(
        description="Package newly crawled TalentScout jobs per profile and send via SMTP."
    )
    parser.add_argument("--profile", type=str, default=None, help="Specific profile ID or name (default: all delivery-enabled profiles).")
    parser.add_argument("--run-id", type=str, default=None, help="Run identifier recorded in manifest and profile_deliveries.")
    parser.add_argument("--out-dir", type=str, default="logs/packages", help="Directory where .zip packages are written.")
    parser.add_argument("--telemetry", type=str, default="logs/scour_summary_latest.json", help="Path to scour telemetry JSON to bundle.")
    parser.add_argument("--no-sync-env", action="store_true", help="Do not sync TALENTSCOUT_PROFILES_JSON / RECIPIENT_EMAIL before running.")
    parser.add_argument("--dry-run", action="store_true", help="Build .zip package(s) without sending SMTP emails or recording deliveries.")
    parser.add_argument("--skip-email", action="store_true", help="Build .zip package(s) without sending SMTP emails.")
    cli_args = parser.parse_args(args)

    summary = run_packaging_and_delivery(
        profile_arg=cli_args.profile,
        run_id=cli_args.run_id,
        out_dir=cli_args.out_dir,
        telemetry_path=cli_args.telemetry,
        sync_env=not cli_args.no_sync_env,
        dry_run=cli_args.dry_run,
        skip_email=cli_args.skip_email,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
