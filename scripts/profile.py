import json
import sqlite3
import threading
import os
import sys
import datetime
from pathlib import Path
from typing import Optional, Any, List, Dict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from scripts.database import create_connection

SCHEMA_VERSION = 1
_CACHE_LOCK = threading.Lock()
_ACTIVE_CACHE: dict = {"id": None, "name": None, "config": None}

def default_config() -> dict:
    """Return default profile configuration based on TalentScout base_skillset defaults."""
    return {
        "schema_version": SCHEMA_VERSION,
        "meta": {
            "candidate_name": "Thomas S. Snyder",
            "experience_years": 26,
            "experience_target": "senior"
        },
        "search": {
            "default_terms": ["QA Engineer", "SDET", "Senior QA", "Test Automation"],
            "title_keywords_positive": ["QA", "SDET", "Test", "Quality", "Automation"],
            "title_keywords_negative": ["Python Developer", "Backend Engineer"],
            "relevant_tech": [
                "Karate Framework", "API Testing", "Mobile Testing", "Kubernetes", "Helm",
                "Docker", "Graphite", "Grafana", "Visual Studio", "Team Foundation Server",
                "Xbox SDK", "Manual Testing", "Black Box Testing", "Regression Testing",
                "Jira", "AWS", "Git", "DevTools", "SDET", "Microservice", "Fiddler", "Mitm",
                "SaaS", "Browserstack", "Optimizely", "Salesforce", "Confluence", "TestRail"
            ]
        },
        "scoring": {
            "min_relevance_score": 40,
            "weights": {
                "title": 30,
                "tech": 35,
                "experience": 20,
                "signal": 15
            },
            "core_tech": [
                "Karate Framework", "API Testing", "Mobile Testing", "Automation Management",
                "Game Testing", "Agentic AI", "Kubernetes", "Helm", "Docker", "AWS", "Git",
                "SDET", "Test Planning", "TestRail", "Test Cases"
            ],
            "disqualified_skills": ["Python", "C++", "C#"],
            "experience_bonuses": {
                "fresher": -15,
                "junior": -5,
                "mid": 5,
                "senior": 15,
                "any": 5
            }
        },
        "location": {
            "country": "US",
            "country_name": "United States",
            "state": "Washington",
            "state_code": "WA",
            "city": "Redmond",
            "postal_code": "98052",
            "allowed_countries": ["US", "USA", "United States"],
            "target_states": ["WA", "Washington"],
            "preferred_cities": ["Seattle", "Redmond", "Bellevue", "Kirkland"],
            "preferred_locations": ["Seattle", "Redmond", "Bellevue", "Remote"],
            "allow_remote": True,
            "require_local_or_remote": True,
            "location_positive": ["washington", "wa", "remote", "nationwide", "usa", "seattle", "redmond", "bellevue", "kirkland"],
            "location_negative": ["india only", "latam only", "uk only", "europe only"]
        },
        "llm": {
            "provider": "local",
            "model_name": "gemma-3-1B-it-QAT-Q4_0.gguf",
            "custom_endpoint": "",
            "api_keys": {
                "gemini": "",
                "openai": "",
                "anthropic": "",
                "groq": "",
                "openrouter": "",
                "custom": ""
            }
        },
        "delivery": {
            "enabled": False,
            "recipient_email": "",
            "min_score": 40,
            "max_jobs": 50,
            "include_formats": ["json", "csv", "md"],
            "send_empty_digest": False
        }
    }

def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def validate_config(config: dict) -> dict:
    base = default_config()
    merged = _deep_merge(base, config or {})
    
    target = merged.get("meta", {}).get("experience_target", "senior")
    if target not in ("fresher", "junior", "mid", "senior", "any"):
        merged["meta"]["experience_target"] = "senior"
        
    w = merged.get("scoring", {}).get("weights", {})
    for k in ("title", "tech", "experience", "signal"):
        try:
            w[k] = max(0, int(w.get(k, base["scoring"]["weights"][k])))
        except (TypeError, ValueError):
            w[k] = base["scoring"]["weights"][k]
    merged["scoring"]["weights"] = w

    # Validate location block
    loc_cfg = merged.get("location", {})
    if not isinstance(loc_cfg.get("allowed_countries"), list):
        loc_cfg["allowed_countries"] = ["US", "USA", "United States"]
    if not isinstance(loc_cfg.get("target_states"), list):
        loc_cfg["target_states"] = [loc_cfg.get("state", "Washington"), loc_cfg.get("state_code", "WA")] if loc_cfg.get("state") else ["WA", "Washington"]
    if not isinstance(loc_cfg.get("preferred_cities"), list):
        loc_cfg["preferred_cities"] = [loc_cfg.get("city", "Redmond")] if loc_cfg.get("city") else ["Seattle", "Redmond", "Bellevue", "Kirkland"]
    if "require_local_or_remote" not in loc_cfg:
        loc_cfg["require_local_or_remote"] = loc_cfg.get("require_wa_or_remote", True)
    if "allow_remote" not in loc_cfg:
        loc_cfg["allow_remote"] = True
    merged["location"] = loc_cfg

    # Validate LLM block
    llm_cfg = merged.get("llm", {})
    valid_providers = ("local", "gemini", "openai", "anthropic", "groq", "openrouter", "custom")
    if llm_cfg.get("provider") not in valid_providers:
        llm_cfg["provider"] = "local"
    if not isinstance(llm_cfg.get("api_keys"), dict):
        llm_cfg["api_keys"] = {}
    for key_name in ("gemini", "openai", "anthropic", "groq", "openrouter", "custom"):
        if key_name not in llm_cfg["api_keys"]:
            llm_cfg["api_keys"][key_name] = ""
    merged["llm"] = llm_cfg

    # Validate delivery block
    deliv_cfg = merged.get("delivery", {})
    if not isinstance(deliv_cfg, dict):
        deliv_cfg = {}
    deliv_cfg["enabled"] = bool(deliv_cfg.get("enabled", False))
    deliv_cfg["recipient_email"] = str(deliv_cfg.get("recipient_email", "") or "").strip()
    try:
        deliv_cfg["min_score"] = max(0, min(100, int(deliv_cfg.get("min_score", 40))))
    except (TypeError, ValueError):
        deliv_cfg["min_score"] = 40
    try:
        deliv_cfg["max_jobs"] = max(1, min(500, int(deliv_cfg.get("max_jobs", 50))))
    except (TypeError, ValueError):
        deliv_cfg["max_jobs"] = 50
    raw_formats = deliv_cfg.get("include_formats", ["json", "csv", "md"])
    if not isinstance(raw_formats, list):
        raw_formats = ["json", "csv", "md"]
    allowed_formats = ("json", "csv", "md")
    clean_formats = [f.lower() for f in raw_formats if isinstance(f, str) and f.lower() in allowed_formats]
    deliv_cfg["include_formats"] = clean_formats or ["json", "csv", "md"]
    deliv_cfg["send_empty_digest"] = bool(deliv_cfg.get("send_empty_digest", False))
    merged["delivery"] = deliv_cfg

    return merged

def get_user_location(profile_or_id: Optional[Any] = None) -> dict:
    """
    Retrieve candidate location properties and search constraints from a profile.
    If no profile is provided, uses the active profile.
    """
    if profile_or_id is None:
        p = get_active_profile()
        cfg = p.get("config", {})
    elif isinstance(profile_or_id, int):
        p = get_profile(profile_or_id) or get_active_profile()
        cfg = p.get("config", {})
    elif isinstance(profile_or_id, dict):
        cfg = profile_or_id.get("config", profile_or_id)
    else:
        p = get_active_profile()
        cfg = p.get("config", {})
        
    loc = cfg.get("location", {})
    return {
        "country": loc.get("country", "US"),
        "country_name": loc.get("country_name", "United States"),
        "state": loc.get("state", "Washington"),
        "state_code": loc.get("state_code", "WA"),
        "city": loc.get("city", "Redmond"),
        "postal_code": loc.get("postal_code", "98052"),
        "allowed_countries": loc.get("allowed_countries", ["US", "USA", "United States"]),
        "target_states": loc.get("target_states", ["WA", "Washington"]),
        "preferred_cities": loc.get("preferred_cities", ["Seattle", "Redmond", "Bellevue", "Kirkland"]),
        "allow_remote": loc.get("allow_remote", True),
        "require_local_or_remote": loc.get("require_local_or_remote", loc.get("require_wa_or_remote", True)),
        "location_positive": loc.get("location_positive", ["washington", "wa", "remote", "nationwide", "usa", "seattle", "redmond", "bellevue", "kirkland"]),
        "location_negative": loc.get("location_negative", [])
    }



def invalidate_cache() -> None:
    with _CACHE_LOCK:
        _ACTIVE_CACHE["id"] = None
        _ACTIVE_CACHE["name"] = None
        _ACTIVE_CACHE["config"] = None

def _cache_set(pid: int, name: str, config: dict) -> None:
    with _CACHE_LOCK:
        _ACTIVE_CACHE["id"] = pid
        _ACTIVE_CACHE["name"] = name
        _ACTIVE_CACHE["config"] = config

def get_active_profile() -> dict:
    with _CACHE_LOCK:
        if _ACTIVE_CACHE["id"] is not None:
            return {
                "id": _ACTIVE_CACHE["id"],
                "name": _ACTIVE_CACHE["name"],
                "config": _ACTIVE_CACHE["config"]
            }

    conn = create_connection()
    if not conn:
        return {"id": 0, "name": "Default Fallback", "config": default_config()}

    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM app_settings WHERE key = 'active_profile_id'")
        row = cursor.fetchone()
        active_id = int(row["value"]) if row else None

        if active_id:
            cursor.execute("SELECT * FROM profiles WHERE id = ?", (active_id,))
            p_row = cursor.fetchone()
            if p_row:
                config = validate_config(json.loads(p_row["config"]))
                _cache_set(p_row["id"], p_row["name"], config)
                return {"id": p_row["id"], "name": p_row["name"], "config": config}

        # If no active set, fetch first profile or seed
        cursor.execute("SELECT * FROM profiles ORDER BY id ASC LIMIT 1")
        p_row = cursor.fetchone()
        if p_row:
            config = validate_config(json.loads(p_row["config"]))
            _cache_set(p_row["id"], p_row["name"], config)
            cursor.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('active_profile_id', ?)", (str(p_row["id"]),))
            conn.commit()
            return {"id": p_row["id"], "name": p_row["name"], "config": config}

    except Exception as e:
        print(f"Error fetching active profile: {e}")
    finally:
        conn.close()

    # Fallback to seeded default
    seed_default_profile()
    return get_active_profile()

def seed_default_profile() -> None:
    """Seed DB with default profile from base_skillset.json if profiles table is empty."""
    conn = create_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM profiles")
        count = cursor.fetchone()[0]
        if count > 0:
            return

        config = default_config()
        # Try loading base_skillset.json if present to overlay core_skills
        script_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(script_dir)
        skillset_path = os.path.join(root_dir, "base_skillset.json")
        
        if os.path.exists(skillset_path):
            try:
                with open(skillset_path, 'r', encoding='utf-8') as f:
                    base_data = json.load(f)
                    if "core_skills" in base_data:
                        config["scoring"]["core_tech"] = base_data["core_skills"]
                    if "disqualified_skills" in base_data:
                        config["scoring"]["disqualified_skills"] = base_data["disqualified_skills"]
                    if "name" in base_data:
                        config["meta"]["candidate_name"] = base_data["name"]
                    if "experience_years" in base_data:
                        config["meta"]["experience_years"] = base_data["experience_years"]
                    if "preferred_locations" in base_data:
                        config["location"]["preferred_locations"] = base_data["preferred_locations"]
            except Exception as ex:
                print(f"Warning: Could not overlay base_skillset.json into default profile: {ex}")

        now = datetime.datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO profiles (name, description, config, created_at)
            VALUES (?, ?, ?, ?)
        """, ("Default Profile", "Seeded from base_skillset.json", json.dumps(config), now))
        profile_id = cursor.lastrowid
        cursor.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('active_profile_id', ?)", (str(profile_id),))
        conn.commit()
        print(f"[+] Seeded default profile (ID: {profile_id}) into SQLite database.")
    except Exception as e:
        print(f"Error seeding default profile: {e}")
    finally:
        conn.close()

def list_profiles() -> list[dict]:
    conn = create_connection()
    if not conn:
        return []
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, description, created_at FROM profiles ORDER BY id ASC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_profile(profile_id: int) -> Optional[dict]:
    conn = create_connection()
    if not conn:
        return None
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
        row = cursor.fetchone()
        if row:
            res = dict(row)
            res["config"] = validate_config(json.loads(res["config"]))
            return res
        return None
    finally:
        conn.close()

def create_profile(name: str, description: str, config: dict) -> int:
    conn = create_connection()
    if not conn:
        raise RuntimeError("No DB connection")
    try:
        cursor = conn.cursor()
        valid_cfg = validate_config(config)
        now = datetime.datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO profiles (name, description, config, created_at)
            VALUES (?, ?, ?, ?)
        """, (name, description, json.dumps(valid_cfg), now))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def update_profile(profile_id: int, name: str, description: str, config: dict) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        valid_cfg = validate_config(config)
        cursor.execute("""
            UPDATE profiles SET name = ?, description = ?, config = ? WHERE id = ?
        """, (name, description, json.dumps(valid_cfg), profile_id))
        conn.commit()
        invalidate_cache()
        return cursor.rowcount > 0
    finally:
        conn.close()

def activate_profile(profile_id: int) -> bool:
    conn = create_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM profiles WHERE id = ?", (profile_id,))
        if not cursor.fetchone():
            return False
        cursor.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES ('active_profile_id', ?)", (str(profile_id),))
        conn.commit()
        invalidate_cache()
        return True
    finally:
        conn.close()

def delete_profile(profile_id: int) -> bool:
    active = get_active_profile()
    if active.get("id") == profile_id:
        raise ValueError("Cannot delete active profile")
    
    conn = create_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_profile_by_name(name: str) -> Optional[dict]:
    """Fetch a profile by exact (case-insensitive) name."""
    if not name:
        return None
    conn = create_connection()
    if not conn:
        return None
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles WHERE LOWER(name) = LOWER(?)", (name.strip(),))
        row = cursor.fetchone()
        if row:
            res = dict(row)
            res["config"] = validate_config(json.loads(res["config"]))
            return res
        return None
    finally:
        conn.close()


def upsert_profile_from_dict(entry: dict) -> int:
    """
    Idempotently create or update a profile from a dictionary (e.g. from CI secrets).
    Supports either nested `config` or top-level overrides (`meta`, `search`, `scoring`,
    `location`, `llm`, `delivery`, plus shorthand `recipient_email`).
    """
    if not isinstance(entry, dict) or not entry.get("name"):
        raise ValueError("Profile entry must be a dict with a non-empty 'name'.")

    name = str(entry["name"]).strip()
    description = str(entry.get("description", "Synced from environment profile config"))

    existing = get_profile_by_name(name)
    base_cfg = existing["config"] if existing else default_config()

    override_cfg = dict(entry.get("config", {}) or {})
    for section in ("meta", "search", "scoring", "location", "llm", "delivery"):
        if section in entry and isinstance(entry[section], dict):
            override_cfg[section] = _deep_merge(override_cfg.get(section, {}), entry[section])

    # Shorthand: top-level recipient_email enables delivery automatically unless explicitly disabled
    if entry.get("recipient_email"):
        deliv = dict(override_cfg.get("delivery", {}))
        deliv["recipient_email"] = str(entry["recipient_email"]).strip()
        deliv.setdefault("enabled", True)
        override_cfg["delivery"] = deliv

    merged = validate_config(_deep_merge(base_cfg, override_cfg))

    if existing:
        update_profile(existing["id"], name, description, merged)
        return existing["id"]
    return create_profile(name, description, merged)


def sync_profiles_from_env() -> List[dict]:
    """
    Sync private profile definitions and email delivery targets from environment secrets
    (e.g. GitHub Actions Secrets) into SQLite without committing PII to a public repo.

    Supported env vars:
      - TALENTSCOUT_PROFILES_JSON: JSON list (or single object) of profile definitions.
      - RECIPIENT_EMAIL: Single-user shortcut that enables email delivery on the active profile.
      - DELIVERY_MIN_SCORE / DELIVERY_MAX_JOBS: Optional integer overrides for RECIPIENT_EMAIL mode.
    """
    seed_default_profile()
    synced: List[dict] = []

    raw_profiles = os.environ.get("TALENTSCOUT_PROFILES_JSON", "").strip()
    if raw_profiles:
        parsed = json.loads(raw_profiles)
        if isinstance(parsed, dict):
            parsed = [parsed]
        if not isinstance(parsed, list):
            raise ValueError("TALENTSCOUT_PROFILES_JSON must decode to a JSON object or array.")
        for item in parsed:
            pid = upsert_profile_from_dict(item)
            prof = get_profile(pid)
            if prof:
                synced.append(prof)

    recipient_email = os.environ.get("RECIPIENT_EMAIL", "").strip()
    if recipient_email and not any(
        p["config"].get("delivery", {}).get("enabled") and p["config"].get("delivery", {}).get("recipient_email")
        for p in get_delivery_enabled_profiles()
    ):
        active = get_active_profile()
        cfg = dict(active["config"])
        deliv = dict(cfg.get("delivery", {}))
        deliv["enabled"] = True
        deliv["recipient_email"] = recipient_email
        if os.environ.get("DELIVERY_MIN_SCORE", "").strip():
            try:
                deliv["min_score"] = int(os.environ["DELIVERY_MIN_SCORE"])
            except ValueError:
                pass
        if os.environ.get("DELIVERY_MAX_JOBS", "").strip():
            try:
                deliv["max_jobs"] = int(os.environ["DELIVERY_MAX_JOBS"])
            except ValueError:
                pass
        cfg["delivery"] = deliv
        update_profile(active["id"], active["name"], active.get("description", "Default Profile"), cfg)
        refreshed = get_profile(active["id"])
        if refreshed:
            synced.append(refreshed)

    return synced


def get_delivery_enabled_profiles() -> List[dict]:
    """Return all profiles configured with delivery.enabled=True and a non-empty recipient_email."""
    results: List[dict] = []
    for summary in list_profiles():
        full = get_profile(summary["id"])
        if not full:
            continue
        deliv = full.get("config", {}).get("delivery", {})
        if deliv.get("enabled") and deliv.get("recipient_email"):
            results.append(full)
    return results

