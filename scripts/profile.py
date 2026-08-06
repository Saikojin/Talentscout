import json
import sqlite3
import threading
import os
import sys
import datetime
from pathlib import Path
from typing import Optional

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
            "preferred_locations": ["Seattle", "Redmond", "Bellevue", "Remote"],
            "location_positive": ["washington", "wa", "remote", "nationwide", "usa", "seattle", "redmond", "bellevue", "kirkland"],
            "location_negative": ["india only", "latam only", "uk only", "europe only"],
            "require_wa_or_remote": True
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
    return merged

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
