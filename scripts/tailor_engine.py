import os
import sys
import json
import re
import urllib.request
import urllib.error
import subprocess
import time
from typing import Dict, Any, Optional, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from scripts.database import create_connection

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:8000")
RESUME_JSON_PATH = os.path.join(BASE_DIR, "resume", "data", "resume.json")
TAILORED_DIR = os.path.join(BASE_DIR, "tailored_outputs")
os.makedirs(TAILORED_DIR, exist_ok=True)

_LLM_PROCESS: Optional[subprocess.Popen] = None

# Model directories to scan
MODEL_DIRS = [
    os.path.join(BASE_DIR, "llmworkbench", "models"),
    r"D:\DevWorkspace\LLMWorkbench\backend\models"
]

def get_candidate_data() -> Dict[str, Any]:
    """Load the candidate's canonical resume data."""
    if os.path.exists(RESUME_JSON_PATH):
        try:
            with open(RESUME_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading resume.json: {e}")
    return {}

def list_local_models() -> List[str]:
    """Scan all model directories for available GGUF files."""
    models = set()
    for d in MODEL_DIRS:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.endswith(".gguf"):
                    models.add(f)
    return sorted(list(models))

def check_llm_status() -> Dict[str, Any]:
    """Check if the LLMWorkbench API is running and responsive."""
    try:
        req = urllib.request.Request(f"{LLM_BASE_URL}/api/status", headers={"User-Agent": "TalentScout-App"})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            active_model = data.get("active_model")
            return {
                "online": True,
                "active_model": active_model if (active_model and active_model != "None") else "gemma-3-1B-it-QAT-Q4_0.gguf",
                "backend": data.get("backend", "gguf"),
                "available_models": list_local_models()
            }
    except Exception:
        try:
            req = urllib.request.Request(f"{LLM_BASE_URL}/v1/models", headers={"User-Agent": "TalentScout-App"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                return {
                    "online": True,
                    "active_model": "Active",
                    "backend": "gguf",
                    "available_models": list_local_models()
                }
        except Exception:
            return {
                "online": False,
                "active_model": None,
                "backend": "offline",
                "available_models": list_local_models()
            }

def get_default_fast_model(available_models: List[str]) -> str:
    """Select the best fast default model for quick tailoring."""
    preferences = [
        "gemma-3-1B-it-QAT-Q4_0.gguf",
        "Hunyuan-0.5B-Instruct_Q2_K.gguf",
        "LFM2.5-1.2B-Thinking-Q4_0.gguf",
        "Nebulos-Distill-Qwen3-0.6B.gguf"
    ]
    for pref in preferences:
        if pref in available_models:
            return pref
    valid = [m for m in available_models if not m.startswith("acestep-")]
    return valid[0] if valid else (available_models[0] if available_models else "gemma-3-1B-it-QAT-Q4_0.gguf")

def start_llm_server(model_name: Optional[str] = None) -> Dict[str, Any]:
    """Start the LLMWorkbench backend server in the background."""
    global _LLM_PROCESS
    
    # Check if already running
    status = check_llm_status()
    if status.get("online"):
        return {"status": "already_running", "active_model": status.get("active_model")}

    available = list_local_models()
    if not available and not model_name:
        return {"status": "error", "message": "No .gguf model files found in llmworkbench/models/."}

    selected_model = model_name or get_default_fast_model(available)

    # Try starting bundled main.py or fallback script
    python_exe = sys.executable
    server_script = os.path.join(BASE_DIR, "llmworkbench", "main.py")
    if not os.path.exists(server_script):
        server_script = r"D:\DevWorkspace\LLMWorkbench\backend\main.py"

    log_file_path = os.path.join(BASE_DIR, "llmworkbench", "backend.log")
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

    cmd = [python_exe, server_script, "--model", selected_model]
    
    try:
        env = os.environ.copy()
        localmind_src = r"D:\DevWorkspace\LocalMind\src"
        python_paths = [os.path.dirname(server_script), BASE_DIR]
        if os.path.exists(localmind_src):
            python_paths.append(localmind_src)
        env["PYTHONPATH"] = ";".join(python_paths) + f";{env.get('PYTHONPATH', '')}"
        
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS

        log_out = open(log_file_path, "a", encoding="utf-8")
        log_out.write(f"\n--- Starting LLM server with model: {selected_model} at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        log_out.flush()

        _LLM_PROCESS = subprocess.Popen(
            cmd,
            cwd=os.path.dirname(server_script),
            env=env,
            stdout=log_out,
            stderr=log_out,
            creationflags=creationflags
        )

        # Polling for readiness (up to 10 seconds)
        for _ in range(20):
            time.sleep(0.5)
            st = check_llm_status()
            if st.get("online"):
                return {"status": "started", "active_model": selected_model}

        return {"status": "starting", "message": "Server process launched, waiting for model initialization."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def stop_llm_server() -> Dict[str, Any]:
    """Stop the background LLM process if managed, and clean up worker ports 8000 and 8080."""
    global _LLM_PROCESS
    if _LLM_PROCESS:
        try:
            _LLM_PROCESS.terminate()
            _LLM_PROCESS.kill()
        except Exception:
            pass
        _LLM_PROCESS = None
            
    # Terminate any remaining processes on port 8000 (LLM API) and 8080 (llama-server worker) on Windows
    if sys.platform == "win32":
        for target_port in [8000, 8080]:
            try:
                out = subprocess.check_output(f"netstat -ano | findstr :{target_port}", shell=True).decode()
                pids = set()
                for line in out.strip().splitlines():
                    parts = line.strip().split()
                    if len(parts) >= 5 and "LISTENING" in line:
                        pids.add(parts[-1])
                for pid in pids:
                    subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    return {"status": "stopped", "message": "LLM process and inference worker terminated."}

import sqlite3

def sanitize_folder_name(name: str) -> str:
    """Sanitize string for folder names."""
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\s]', '', name).strip()
    return re.sub(r'\s+', '_', cleaned)

def get_job_details(job_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve job details from SQLite by job_id."""
    conn = create_connection()
    if not conn:
        return None
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        if not row:
            return None
        
        job = dict(row)
        if job.get("missing_skills") and isinstance(job["missing_skills"], str):
            try: job["missing_skills"] = json.loads(job["missing_skills"])
            except: pass
        if job.get("matched_skills") and isinstance(job["matched_skills"], str):
            try: job["matched_skills"] = json.loads(job["matched_skills"])
            except: pass
        return job
    finally:
        conn.close()

def query_local_llm(messages: List[Dict[str, str]], model: Optional[str] = None, max_tokens: int = 2048) -> str:
    """Send chat completions request to the local LLMWorkbench OpenAI endpoint."""
    url = f"{LLM_BASE_URL}/v1/chat/completions"
    payload = {
        "model": model or "local",
        "messages": messages,
        "temperature": 0.5,
        "max_tokens": max_tokens
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "TalentScout-Engine"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            choices = res.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
    except Exception as e:
        print(f"query_local_llm call failed: {e}")
    return ""

def query_gemini_llm(messages: List[Dict[str, str]], api_key: str = "", model: str = "gemini-2.0-flash", max_tokens: int = 2500) -> str:
    """Send chat request to Google Gemini REST API."""
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        raise ValueError("Google Gemini API Key is missing. Add it to your Profile or set GEMINI_API_KEY.")

    api_key = api_key.strip()
    
    # Sanitize model name: strip whitespace and leading 'models/' prefix
    model_clean = (model or "").strip()
    if model_clean.startswith("models/"):
        model_clean = model_clean[len("models/"):]
    if not model_clean or model_clean.endswith(".gguf") or any(k in model_clean.lower() for k in ["gemma", "llama", "qwen", "mistral", "gpt-", "claude-"]):
        model_clean = "gemini-2.0-flash"

    system_text = ""
    contents = []
    for m in messages:
        if m["role"] == "system":
            system_text += m["content"] + "\n"
        elif m["role"] in ("user", "assistant"):
            role_name = "user" if m["role"] == "user" else "model"
            contents.append({
                "role": role_name,
                "parts": [{"text": m["content"]}]
            })

    payload: Dict[str, Any] = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.5,
            "maxOutputTokens": max_tokens
        }
    }
    if system_text.strip():
        payload["systemInstruction"] = {
            "parts": [{"text": system_text.strip()}]
        }

    urls_to_try = [
        f"https://generativelanguage.googleapis.com/v1beta/models/{model_clean}:generateContent?key={api_key}",
        f"https://generativelanguage.googleapis.com/v1/models/{model_clean}:generateContent?key={api_key}"
    ]

    last_err: Optional[Exception] = None
    for url in urls_to_try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "TalentScout-Engine"}
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                candidates = res.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", []) if isinstance(content, dict) else []
                    texts = [p.get("text", "") for p in parts if isinstance(p, dict) and "text" in p]
                    full_text = "".join(texts).strip()
                    if full_text:
                        return full_text
                    finish_reason = candidates[0].get("finishReason")
                    if finish_reason:
                        return f"OK (finish: {finish_reason})"
                return "Connection verified (HTTP 200)"
        except urllib.error.HTTPError as e:
            err_msg = ""
            try:
                raw_body = e.read().decode("utf-8", errors="ignore")
                err_json = json.loads(raw_body)
                err_info = err_json.get("error", {})
                if isinstance(err_info, dict):
                    err_msg = err_info.get("message", raw_body)
                elif isinstance(err_info, str):
                    err_msg = err_info
            except Exception:
                pass
            last_err = RuntimeError(f"Google Gemini Error ({e.code}): {err_msg or e.reason}")
            # If 404 on v1beta, attempt fallback to v1 endpoint
            if e.code == 404 and url == urls_to_try[0]:
                continue
            raise last_err
        except Exception as e:
            last_err = e
            raise last_err

    if last_err:
        raise last_err
    return ""

def query_openai_compatible_llm(messages: List[Dict[str, str]], api_base: str, api_key: str = "", model: str = "gpt-4o-mini", max_tokens: int = 2500) -> str:
    """Send chat request to OpenAI, Groq, OpenRouter, or custom OpenAI-compatible endpoints."""
    url = f"{api_base.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.5,
        "max_tokens": max_tokens
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "TalentScout-Engine"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key.strip()}"

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            choices = res.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body_raw = e.read().decode("utf-8", errors="ignore")
            err_json = json.loads(body_raw)
            err_obj = err_json.get("error", {})
            if isinstance(err_obj, dict):
                body = err_obj.get("message", body_raw)
            elif isinstance(err_obj, str):
                body = err_obj
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code}: {body or e.reason}")
    return ""

def query_anthropic_llm(messages: List[Dict[str, str]], api_key: str = "", model: str = "claude-3-5-sonnet-20241022", max_tokens: int = 2500) -> str:
    """Send message request to Anthropic REST API."""
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("Anthropic API Key is missing. Add it to your Profile or set ANTHROPIC_API_KEY.")

    api_key = api_key.strip()
    model_clean = (model or "").strip()
    if not model_clean or model_clean.endswith(".gguf") or "gemma" in model_clean:
        model_clean = "claude-3-5-sonnet-20241022"
    url = "https://api.anthropic.com/v1/messages"

    system_text = ""
    user_msgs = []
    for m in messages:
        if m["role"] == "system":
            system_text += m["content"] + "\n"
        elif m["role"] in ("user", "assistant"):
            user_msgs.append({"role": m["role"], "content": m["content"]})

    payload: Dict[str, Any] = {
        "model": model_clean,
        "max_tokens": max_tokens,
        "temperature": 0.5,
        "messages": user_msgs
    }
    if system_text.strip():
        payload["system"] = system_text.strip()

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "User-Agent": "TalentScout-Engine"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            content = res.get("content", [])
            if content:
                return content[0].get("text", "").strip()
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body_raw = e.read().decode("utf-8", errors="ignore")
            err_json = json.loads(body_raw)
            err_obj = err_json.get("error", {})
            if isinstance(err_obj, dict):
                body = err_obj.get("message", body_raw)
            elif isinstance(err_obj, str):
                body = err_obj
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code}: {body or e.reason}")
    return ""

def query_ai_service(messages: List[Dict[str, str]], provider: str = "local", model: Optional[str] = None, profile_llm_cfg: Optional[Dict[str, Any]] = None, max_tokens: int = 2500) -> str:
    """Unified dispatcher for Local GGUF, Google Gemini, OpenAI, Anthropic, Groq, OpenRouter, and Custom endpoints."""
    cfg = profile_llm_cfg or {}
    api_keys = cfg.get("api_keys", {})
    provider = (provider or cfg.get("provider", "local")).lower()

    if provider == "gemini":
        key = api_keys.get("gemini") or os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
        return query_gemini_llm(messages, api_key=key, model=model or cfg.get("model_name") or "gemini-2.0-flash", max_tokens=max_tokens)
    elif provider == "openai":
        key = api_keys.get("openai") or os.environ.get("OPENAI_API_KEY", "")
        return query_openai_compatible_llm(messages, api_base="https://api.openai.com/v1", api_key=key, model=model or cfg.get("model_name") or "gpt-4o-mini", max_tokens=max_tokens)
    elif provider == "anthropic":
        key = api_keys.get("anthropic") or os.environ.get("ANTHROPIC_API_KEY", "")
        return query_anthropic_llm(messages, api_key=key, model=model or cfg.get("model_name") or "claude-3-5-sonnet-20241022", max_tokens=max_tokens)
    elif provider == "groq":
        key = api_keys.get("groq") or os.environ.get("GROQ_API_KEY", "")
        return query_openai_compatible_llm(messages, api_base="https://api.groq.com/openai/v1", api_key=key, model=model or cfg.get("model_name") or "llama-3.3-70b-versatile", max_tokens=max_tokens)
    elif provider == "openrouter":
        key = api_keys.get("openrouter") or os.environ.get("OPENROUTER_API_KEY", "")
        return query_openai_compatible_llm(messages, api_base="https://openrouter.ai/api/v1", api_key=key, model=model or cfg.get("model_name") or "meta-llama/llama-3.3-70b-instruct", max_tokens=max_tokens)
    elif provider == "custom":
        endpoint = cfg.get("custom_endpoint") or os.environ.get("CUSTOM_API_BASE", "http://localhost:8000/v1")
        key = api_keys.get("custom") or os.environ.get("CUSTOM_API_KEY", "")
        return query_openai_compatible_llm(messages, api_base=endpoint, api_key=key, model=model or cfg.get("model_name") or "default", max_tokens=max_tokens)
    else:
        # Default to local LLMWorkbench
        return query_local_llm(messages, model=model or cfg.get("model_name"), max_tokens=max_tokens)

def test_provider_connection(provider: str, model: Optional[str] = None, api_key: str = "", custom_endpoint: str = "") -> Dict[str, Any]:
    """Test ping a specific provider with given credentials."""
    start_time = time.time()
    test_messages = [
        {"role": "user", "content": "Ping test: confirm connection with a brief response."}
    ]
    try:
        p = provider.lower().strip()
        api_key = (api_key or "").strip()
        if p == "gemini":
            resp = query_gemini_llm(test_messages, api_key=api_key, model=model or "gemini-2.0-flash", max_tokens=100)
        elif p == "openai":
            resp = query_openai_compatible_llm(test_messages, api_base="https://api.openai.com/v1", api_key=api_key, model=model or "gpt-4o-mini", max_tokens=100)
        elif p == "anthropic":
            resp = query_anthropic_llm(test_messages, api_key=api_key, model=model or "claude-3-5-sonnet-20241022", max_tokens=100)
        elif p == "groq":
            resp = query_openai_compatible_llm(test_messages, api_base="https://api.groq.com/openai/v1", api_key=api_key, model=model or "llama-3.3-70b-versatile", max_tokens=100)
        elif p == "openrouter":
            resp = query_openai_compatible_llm(test_messages, api_base="https://openrouter.ai/api/v1", api_key=api_key, model=model or "meta-llama/llama-3.3-70b-instruct", max_tokens=100)
        elif p == "custom":
            resp = query_openai_compatible_llm(test_messages, api_base=custom_endpoint or "http://localhost:8000/v1", api_key=api_key, model=model or "default", max_tokens=100)
        else: # local
            resp = query_local_llm(test_messages, model=model, max_tokens=100)
            
        elapsed = round((time.time() - start_time) * 1000, 1)
        # If no HTTPError exception occurred, the connection succeeded
        return {
            "success": True,
            "provider": provider,
            "model": model,
            "response": resp or "Connection verified (HTTP 200)",
            "latency_ms": elapsed
        }
    except Exception as e:
        elapsed = round((time.time() - start_time) * 1000, 1)
        return {
            "success": False,
            "provider": provider,
            "error": str(e),
            "latency_ms": elapsed
        }

# ─────────────────────────────────────────────────────────────────────────────
# CANONICAL RESUME ATS STYLES & COVER LETTER TARGET AUDIENCES
# ─────────────────────────────────────────────────────────────────────────────

RESUME_STYLES: List[str] = ["STANDARD", "CARL", "CAR", "STAR", "LPS", "ELITE", "WHO"]

RESUME_STYLE_META: Dict[str, Dict[str, str]] = {
    "STANDARD": {
        "label": "Standard",
        "subtitle": "Clean ATS Highlights + Tech Stack",
        "filename_md": "Resume.md",
        "filename_docx": "Resume.docx",
    },
    "CARL": {
        "label": "CARL",
        "subtitle": "Context · Action · Result · Learning",
        "filename_md": "Resume_ATS_CARL.md",
        "filename_docx": "Resume_ATS_CARL.docx",
    },
    "CAR": {
        "label": "CAR",
        "subtitle": "Challenge · Action · Result",
        "filename_md": "Resume_ATS_CAR.md",
        "filename_docx": "Resume_ATS_CAR.docx",
    },
    "STAR": {
        "label": "STAR",
        "subtitle": "Situation · Task · Action · Result",
        "filename_md": "Resume_ATS_STAR.md",
        "filename_docx": "Resume_ATS_STAR.docx",
    },
    "LPS": {
        "label": "LPS",
        "subtitle": "Leadership · Problem-Solving · Success",
        "filename_md": "Resume_ATS_LPS.md",
        "filename_docx": "Resume_ATS_LPS.docx",
    },
    "ELITE": {
        "label": "ELITE",
        "subtitle": "Elevate · Leverage · Illustrate · Transfer · Execute",
        "filename_md": "Resume_ATS_ELITE.md",
        "filename_docx": "Resume_ATS_ELITE.docx",
    },
    "WHO": {
        "label": "WHO",
        "subtitle": "What · How · Outcome",
        "filename_md": "Resume_ATS_WHO.md",
        "filename_docx": "Resume_ATS_WHO.docx",
    },
}

COVER_LETTER_TONES: List[str] = ["jd_informed", "hr", "cto", "ceo"]

COVER_LETTER_TONE_META: Dict[str, Dict[str, str]] = {
    "jd_informed": {
        "label": "JD-Informed",
        "audience": "Hiring Team (JD-Aligned)",
        "description": "Maps job description requirements & matched skills directly to concrete career wins and AI/agentic systems.",
        "filename_md": "Cover_Letter_JD_Informed.md",
        "filename_docx": "Cover_Letter_JD_Informed.docx",
    },
    "hr": {
        "label": "HR / Recruiter",
        "audience": "Recruiting & Talent Acquisition",
        "description": "Warm, ultra-scannable checklist pitch emphasizing experience span, location readiness, clear metrics, and collaboration.",
        "filename_md": "Cover_Letter_HR.md",
        "filename_docx": "Cover_Letter_HR.docx",
    },
    "cto": {
        "label": "CTO / Technical",
        "audience": "CTO / VP Engineering / Technical Lead",
        "description": "Peer-to-peer systems architecture voice highlighting zero-to-1 frameworks, kernel-to-cloud diagnostics, MCP harnesses, and deterministic AI evals.",
        "filename_md": "Cover_Letter_CTO.md",
        "filename_docx": "Cover_Letter_CTO.docx",
    },
    "ceo": {
        "label": "CEO / Executive",
        "audience": "CEO / Founder / Executive Leadership",
        "description": "Concise business-outcome framing focused on ROI, release velocity, risk containment, org scaling, and AI force-multiplication.",
        "filename_md": "Cover_Letter_CEO.md",
        "filename_docx": "Cover_Letter_CEO.docx",
    },
}

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "your", "will", "have",
    "are", "our", "you", "who", "work", "team", "role", "experience", "years",
    "strong", "ability", "using", "across", "build", "building", "including",
    "skills", "knowledge", "preferred", "required", "responsibilities", "about",
    "company", "position", "candidate", "looking", "join", "must", "should",
    "such", "well", "high", "new", "their", "them", "they", "into", "more",
    "than", "other", "all", "any", "can", "also", "been", "being", "through",
}


def _clean_clause(text: str) -> str:
    return str(text or "").strip().rstrip(".")


def _lower_first(text: str) -> str:
    s = _clean_clause(text)
    if not s:
        return ""
    if re.match(r"^[A-Z]{2,}", s):
        return s
    return s[0].lower() + s[1:]


def _format_year_range(job_entry: Dict[str, Any]) -> str:
    start = str(job_entry.get("startDate") or "")[:7]
    end = str(job_entry.get("endDate") or "")[:7]
    return f"{start or 'N/A'} – {end or 'Present'}"


def format_work_entry_ats(job_entry: Dict[str, Any], style: str = "CAR") -> List[str]:
    """Python mirror of resume/compiler/atsFormatter.js supporting CAR, CARL, STAR, LPS, ELITE, WHO."""
    norm = (style or "CAR").upper()
    ats_bullets = job_entry.get("atsBullets") or {}
    if isinstance(ats_bullets.get(norm), list) and len(ats_bullets[norm]) > 0:
        return [str(b).strip() for b in ats_bullets[norm] if str(b).strip()]

    challenges = job_entry.get("challenges") or []
    responsibilities = job_entry.get("keyResponsibilities") or []
    wins = job_entry.get("wins") or []
    highlights = job_entry.get("highlights") or []
    tools = job_entry.get("toolsUsed") or []
    skills = job_entry.get("skillsUsed") or []
    lessons = job_entry.get("lessonsLearned") or []

    bullets: List[str] = []
    max_count = max(len(wins), len(highlights), len(responsibilities), 1)
    summary_raw = str(job_entry.get("summary") or "")
    summary_first = _clean_clause(summary_raw.split(".")[0]) if summary_raw else f"Targeted {job_entry.get('name', 'company')} initiatives"
    tool_str = ", ".join(tools[:3]) if tools else "modern engineering tooling"
    skill_str = ", ".join(skills[:2]) if skills else "technical subject matter expertise"

    for i in range(max_count):
        raw_win = (
            wins[i] if i < len(wins)
            else highlights[i] if i < len(highlights)
            else responsibilities[i] if i < len(responsibilities)
            else ""
        )
        if not raw_win:
            continue

        win = _clean_clause(raw_win)
        challenge = _clean_clause(
            challenges[i] if i < len(challenges)
            else (challenges[0] if challenges else "Addressing key quality and process bottlenecks")
        )
        resp = _clean_clause(
            responsibilities[i] if i < len(responsibilities)
            else (responsibilities[0] if responsibilities else "executed key engineering deliverables")
        )
        lesson = _clean_clause(
            lessons[i] if i < len(lessons)
            else (lessons[0] if lessons else "Standardizing repeatable quality workflows and documentation accelerates engineering velocity")
        )

        if norm == "CARL":
            if i < len(challenges):
                context = f"{summary_first}; faced {_lower_first(challenges[i])}"
            else:
                context = f"{summary_first} while addressing {_lower_first(challenge)}"
            bullets.append(
                f"Context: {context}. Action: {resp} utilizing {tool_str}. Result: {win}. Learning: {lesson}."
            )
        elif norm == "STAR":
            bullets.append(
                f"[Situation] {summary_first}. [Task] Focused on {_lower_first(resp)}. [Action] Leveraged {tool_str} to overcome: {_lower_first(challenge)}. [Result] {win}."
            )
        elif norm == "LPS":
            tags = job_entry.get("tags") or []
            lead_verb = "Spearheaded" if "leadership" in tags else "Drove"
            bullets.append(
                f"{lead_verb} solution for {_lower_first(challenge)} by applying {skill_str}; successfully achieved: {win}."
            )
        elif norm == "ELITE":
            bullets.append(
                f"Elevated team capacity by leveraging {tool_str} to tackle {_lower_first(challenge)}; illustrated through {win}, transferring learnings to {_lower_first(lesson)}."
            )
        elif norm == "WHO":
            bullets.append(f"What: {resp}. How: Utilized {tool_str} and {skill_str}. Outcome: {win}.")
        else:
            # CAR default
            bullets.append(f"Challenge: {challenge}. Action: {resp} utilizing {tool_str}. Result: {win}.")

    return bullets


def extract_jd_signals(job_description: str, job: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Extract matched skills, JD keywords, requirement snippets, and domain focus from job + optional JD."""
    matched = [str(s) for s in (job.get("matched_skills") or []) if s]
    missing = [str(s) for s in (job.get("missing_skills") or []) if s]
    jd_text = (job_description or job.get("description") or "").strip()

    # Build candidate vocabulary for high-signal JD matching
    candidate_vocab: List[str] = []
    for sk in candidate.get("skills") or []:
        candidate_vocab.extend(sk.get("keywords") or [])
    for w in candidate.get("work") or []:
        candidate_vocab.extend(w.get("toolsUsed") or [])
        candidate_vocab.extend(w.get("skillsUsed") or [])
    for p in candidate.get("projects") or []:
        candidate_vocab.extend(p.get("keywords") or [])

    # Deduplicate preserving order
    seen_vocab = set()
    unique_vocab = []
    for term in candidate_vocab:
        low = term.lower()
        if low not in seen_vocab and len(term) >= 2:
            seen_vocab.add(low)
            unique_vocab.append(term)

    jd_matched_terms: List[str] = []
    jd_bullet_highlights: List[str] = []
    if jd_text:
        jd_lower = jd_text.lower()
        for term in unique_vocab:
            if re.search(rf"(?<!\w){re.escape(term.lower())}(?!\w)", jd_lower):
                jd_matched_terms.append(term)

        # Pull up to 3 concrete requirement sentences/bullets from JD
        for raw_line in jd_text.splitlines():
            clean_line = raw_line.strip().lstrip("-*•·").strip()
            if 35 <= len(clean_line) <= 220 and any(
                kw in clean_line.lower()
                for kw in ("automat", "test", "quality", "ai", "agent", "llm", "mcp", "api", "ci/cd", "cloud", "aws", "playwright", "python", "architect", "lead", "scale")
            ):
                jd_bullet_highlights.append(clean_line)
            if len(jd_bullet_highlights) >= 3:
                break

    # Merge matched_skills + jd_matched_terms
    combined_keywords: List[str] = []
    seen_k = set()
    for item in matched + jd_matched_terms:
        low = item.lower()
        if low not in seen_k:
            seen_k.add(low)
            combined_keywords.append(item)

    corpus = f"{job.get('title', '')} {' '.join(combined_keywords)} {jd_text}".lower()
    is_ai_role = any(k in corpus for k in ("ai", "agent", "llm", "mcp", "eval", "genai", "machine learning", "ml", "prompt"))
    is_game_role = any(k in corpus for k in ("game", "unreal", "unity", "godot", "xbox", "console", "3d", "shader", "playtest"))
    is_mobile_role = any(k in corpus for k in ("android", "ios", "mobile", "adb", "appium"))
    is_leadership_role = any(k in corpus for k in ("principal", "staff", "lead", "manager", "architect", "director", "head"))

    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "jd_matched_terms": jd_matched_terms,
        "combined_keywords": combined_keywords,
        "jd_highlights": jd_bullet_highlights,
        "jd_text": jd_text,
        "is_ai_role": is_ai_role,
        "is_game_role": is_game_role,
        "is_mobile_role": is_mobile_role,
        "is_leadership_role": is_leadership_role,
    }


def _select_relevant_work(work_entries: List[Dict[str, Any]], signals: Dict[str, Any], limit: int = 6) -> List[Dict[str, Any]]:
    """Keep top 2 most recent entries (including AI/Agentic R&D + Smartsheet) and score the rest by job relevance."""
    if len(work_entries) <= limit:
        return list(work_entries)

    anchored = list(work_entries[:2])
    remaining = list(work_entries[2:])
    keywords_lower = [k.lower() for k in signals.get("combined_keywords", [])]

    scored = []
    for idx, entry in enumerate(remaining):
        blob = " ".join([
            str(entry.get("name", "")),
            str(entry.get("position", "")),
            str(entry.get("summary", "")),
            " ".join(entry.get("tags") or []),
            " ".join(entry.get("toolsUsed") or []),
            " ".join(entry.get("skillsUsed") or []),
        ]).lower()
        score = sum(2 for kw in keywords_lower if kw in blob)
        if signals.get("is_game_role") and any(t in (entry.get("tags") or []) for t in ("games", "console", "xbox", "nintendo")):
            score += 5
        if signals.get("is_mobile_role") and "mobile" in (entry.get("tags") or []):
            score += 4
        if signals.get("is_leadership_role") and "leadership" in (entry.get("tags") or []):
            score += 2
        # Slight recency bonus
        score += max(0, (len(remaining) - idx) * 0.15)
        scored.append((score, idx, entry))

    scored.sort(key=lambda t: (-t[0], t[1]))
    chosen = [entry for _, _, entry in scored[: max(0, limit - len(anchored))]]
    # Preserve chronological (newest-first) ordering from resume.json
    chosen_ids = {id(e) for e in anchored + chosen}
    return [e for e in work_entries if id(e) in chosen_ids]


def _build_candidate_brief_for_llm(candidate: Dict[str, Any], signals: Dict[str, Any]) -> str:
    """Build a compact, factual candidate dossier dynamically from resume.json for LLM prompts."""
    basics = candidate.get("basics") or {}
    work = _select_relevant_work(candidate.get("work") or [], signals, limit=6)
    projects = candidate.get("projects") or []
    skills = candidate.get("skills") or []

    lines = [
        f"- Name: {basics.get('name', 'Thomas S. Snyder')}",
        f"- Label: {basics.get('label', 'Principal QA Architect & Agentic AI Systems Engineer')}",
        f"- Location: {basics.get('location', {}).get('city', 'Redmond')}, {basics.get('location', {}).get('region', 'Washington')} (Remote-ready)",
        f"- Email: {basics.get('email', '')}",
        f"- Summary: {basics.get('summary', '')}",
        "- Key Roles (Fact-Locked from resume.json):",
    ]
    for w in work:
        wins = "; ".join((w.get("wins") or w.get("highlights") or [])[:2])
        tools = ", ".join((w.get("toolsUsed") or [])[:6])
        lines.append(f"  * {w.get('name')} — {w.get('position')} ({_format_year_range(w)}): {wins} [Tools: {tools}]")

    lines.append("- Flagship AI & Engineering Projects:")
    for p in projects[:4]:
        hl = "; ".join((p.get("highlights") or [])[:2])
        lines.append(f"  * {p.get('name')}: {p.get('description')} ({hl})")

    skill_summary = "; ".join(
        f"{s.get('name')} ({', '.join((s.get('keywords') or [])[:6])})"
        for s in skills[:6]
    )
    lines.append(f"- Core Skill Domains: {skill_summary}")
    return "\n".join(lines)


def build_tailored_resume_md(
    candidate: Dict[str, Any],
    job: Dict[str, Any],
    style: str = "STANDARD",
    signals: Optional[Dict[str, Any]] = None,
    custom_summary: Optional[str] = None,
) -> str:
    """Build a job-tailored resume in STANDARD or any ATS framework (CARL, CAR, STAR, LPS, ELITE, WHO)."""
    norm_style = (style or "STANDARD").upper()
    signals = signals or extract_jd_signals("", job, candidate)
    company = job.get("company", "Target Company")
    title = job.get("title", "Senior QA Engineer")
    basics = candidate.get("basics") or {}
    loc = basics.get("location") or {}
    profiles = basics.get("profiles") or []
    skills = candidate.get("skills") or []
    projects = candidate.get("projects") or []
    education = candidate.get("education") or []
    work = _select_relevant_work(candidate.get("work") or [], signals, limit=6)

    matched_list = signals.get("combined_keywords") or ["Test Automation", "API Testing", "Agentic AI Harnesses", "MCP", "Playwright", "Karate DSL"]
    matched_str = ", ".join(matched_list[:10])
    profile_links = " · ".join(f"[{p.get('network')}]({p.get('url')})" for p in profiles if p.get("url"))

    style_meta = RESUME_STYLE_META.get(norm_style, RESUME_STYLE_META["STANDARD"])
    style_tag = f" ({style_meta['label']} — {style_meta['subtitle']})" if norm_style != "STANDARD" else ""

    if custom_summary and len(custom_summary.strip()) > 60:
        summary_text = custom_summary.strip()
    else:
        ai_angle = (
            "architecting production multi-agent AI harnesses (`SeikoClaw-Harness`, 130+ skills), custom Model Context Protocol (MCP) servers, "
            "tiered semantic memory (`OpenBrain`), self-healing local GGUF runtimes (`LocalMind`), and deterministic Anti-Soft-Pass AI evaluation gates"
        )
        summary_text = (
            f"Principal-level Software Quality Architect and Agentic AI Systems Engineer with 26+ years across Microsoft, Smartsheet, OpenMarket, NVIDIA, and Xbox. "
            f"Targeted for the **{title}** role at **{company}**, aligning directly with **{matched_str}**. "
            f"Proven track record of scaling zero-baseline Karate/Playwright test suites to 1,500+ automated tests (replacing 85% of manual regression) while {ai_angle}."
        )

    lines: List[str] = [
        f"# {basics.get('name', 'Thomas S. Snyder')}",
        f"**{title} — Tailored for {company}{style_tag}**",
        f"{basics.get('email', '')} · {loc.get('city', 'Redmond')}, {loc.get('region', 'Washington')} · {profile_links}",
        "",
        "## Professional Summary",
        summary_text,
        "",
        "## Core Competencies & ATS Skill Matrix",
        f"- **Target Role & JD Matched Keywords:** {' · '.join(matched_list[:14])}",
    ]

    for sk in skills:
        kws = sk.get("keywords") or []
        if kws:
            lines.append(f"- **{sk.get('name')}** *({sk.get('level', 'Advanced')})*: {', '.join(kws)}")

    if projects:
        lines.append("")
        lines.append("## Flagship AI, Agentic & Engineering Systems")
        for p in projects[:4]:
            p_url = f" — [{p.get('url')}]({p.get('url')})" if p.get("url") else ""
            lines.append(f"\n### {p.get('name')}{p_url}")
            if p.get("description"):
                lines.append(p["description"])
            for h in (p.get("highlights") or [])[:3]:
                lines.append(f"- {h}")
            if p.get("keywords"):
                lines.append(f"- **Tech Stack & Keywords:** {', '.join(p['keywords'])}")

    lines.append("")
    exp_heading = (
        f"## Targeted Professional Experience ({norm_style} Framework)"
        if norm_style != "STANDARD"
        else "## Targeted Professional Experience"
    )
    lines.append(exp_heading)

    for job_entry in work:
        pos = job_entry.get("position", "")
        co = job_entry.get("name", "")
        loc_str = f" · {job_entry.get('location')}" if job_entry.get("location") else ""
        lines.append(f"\n### {pos} · {co} ({_format_year_range(job_entry)}){loc_str}")
        if job_entry.get("summary"):
            lines.append(f"*{job_entry['summary']}*")

        if norm_style == "STANDARD":
            bullets = (job_entry.get("wins") or job_entry.get("highlights") or [])[:4]
            for b in bullets:
                lines.append(f"- {b}")
        else:
            ats_bullets = format_work_entry_ats(job_entry, norm_style)[:4]
            for b in ats_bullets:
                lines.append(f"- {b}")

        # Dedicated AI-parser-friendly Tech Stack & Keywords line per role
        role_keywords: List[str] = []
        seen_rk = set()
        for kw in (job_entry.get("toolsUsed") or []) + (job_entry.get("skillsUsed") or []):
            low = kw.lower()
            if low not in seen_rk:
                seen_rk.add(low)
                role_keywords.append(kw)
        if role_keywords:
            lines.append(f"- **Tech Stack & Keywords:** {', '.join(role_keywords)}")

    if education:
        lines.append("")
        lines.append("## Continuous Learning & Technical Foundations")
        for edu in education:
            lines.append(f"**{edu.get('studyType', 'Professional Development')} — {edu.get('area', '')}** · *{edu.get('institution', '')}*")
            for c in (edu.get("courses") or [])[:5]:
                lines.append(f"- {c}")

    return "\n".join(lines).strip()


def build_tailored_cover_letter_md(
    candidate: Dict[str, Any],
    job: Dict[str, Any],
    tone: str = "jd_informed",
    signals: Optional[Dict[str, Any]] = None,
) -> str:
    """Deterministic, audience-specific cover letter generator (jd_informed, hr, cto, ceo)."""
    norm_tone = (tone or "jd_informed").lower()
    if norm_tone not in COVER_LETTER_TONES:
        norm_tone = "jd_informed"

    signals = signals or extract_jd_signals("", job, candidate)
    company = job.get("company", "your organization")
    title = job.get("title", "Senior QA Engineer")
    basics = candidate.get("basics") or {}
    loc = basics.get("location") or {}
    name = basics.get("name", "Thomas S. Snyder")
    email = basics.get("email", "Mr.Thomas.Snyder@gmail.com")
    city_state = f"{loc.get('city', 'Redmond')}, {loc.get('region', 'WA')}"

    matched = signals.get("combined_keywords") or ["Test Automation", "API Testing", "Playwright", "Karate DSL", "Agentic AI"]
    top_matched = ", ".join(matched[:6])
    missing = signals.get("missing_skills") or []
    jd_highlights = signals.get("jd_highlights") or []

    header = f"""# {name}
{city_state} · {email} · [LinkedIn]({basics.get('url', '')}) · [GitHub](https://github.com/Saikojin/seikoclaw-harness)
"""

    if norm_tone == "hr":
        return f"""{header}
**Recruiting & Talent Acquisition Team**  
**{company}**  

**RE: {title} — Quick-Scan Fit Summary**

Dear {company} Recruiting Team,

I am excited to apply for the **{title}** role at **{company}**. To make your initial review effortless, here is how my background aligns with what your hiring team is looking for:

- **26+ Years of Quality & Automation Experience:** Enterprise SaaS, cloud APIs, mobile, and hardware/game ecosystems across **Microsoft**, **Smartsheet**, **OpenMarket**, **NVIDIA**, and **Xbox**.
- **Direct Skill Alignment:** Hands-on production depth in **{top_matched}**.
- **Measurable Delivery:** Built Smartsheet's Karate automation suite from **0% to 85% coverage (1,500+ automated tests)**, standardized reusable AWS API testing templates at OpenMarket, and scaled QA teams from a single engineer to full cross-functional squads at Placed Inc.
- **Modern AI & Agentic Tooling:** Actively engineer multi-agent AI harnesses (**SeikoClaw-Harness**), custom **MCP** servers, and deterministic AI verification workflows that accelerate team output without sacrificing reliability.
- **Location & Readiness:** Based in **Redmond, WA** (Pacific Time) and immediately ready for local Seattle/Eastside hybrid or fully remote collaboration.

Beyond technical depth, I am known for clear cross-functional communication, mentoring peers, turning tribal knowledge into onboarding playbooks, and partnering closely with developers and PMs so releases ship smoothly.

I would love to connect for a quick introductory call to discuss how I can support the **{title}** team at **{company}**.

Warm regards,

**{name}**  
Principal QA Architect & Agentic AI Systems Engineer
""".strip()

    if norm_tone == "cto":
        return f"""{header}
**CTO & Engineering Leadership**  
**{company}**  

**RE: {title} — Systems Quality Architecture, Automation & Agentic Verification**

Dear Engineering Leadership at {company},

Most test suites either lag behind product architecture or decay into flaky, low-signal CI gates. Across 26+ years spanning five tenures at **Microsoft**, enterprise SaaS at **Smartsheet**, high-throughput AWS telecom microservices at **OpenMarket**, and my current **AI & Agentic Systems R&D**, I have focused on engineering deterministic verification levers across the entire stack.

For the **{title}** role at **{company}** (specifically targeting **{top_matched}**), here are the architectural patterns I bring day one:

- **Zero-to-One Framework Architecture:** At **Smartsheet**, I architected a Karate DSL + BrowserStack suite from a zero baseline to **1,500+ automated API, UI, and visual regression tests** (replacing 85% of manual regression). At **OpenMarket**, I built reusable API contract templates for AWS/Docker/Terraform cloud migrations.
- **Agentic Harnesses, MCP & Anti-Soft-Pass Verification:** I built **SeikoClaw-Harness** (130+ skills, 24 engineering directives, 5-stage isolated "Goldfish" spec reviews, and adversarial `gate:disproof` falsification gates), **OpenBrain** (SQLite + ChromaDB + SpacetimeDB WASM tiered semantic memory with token compression), and **LocalMind** (self-healing `llama.cpp` GGUF inference recovering from native C++ VRAM decode overflows).
- **Native-Protocol & Root-Cause Depth:** Whether dropping beneath Appium to custom **Pure-ADB** Android harnesses (~50% faster execution), building **Playwright** stealth/DOM-drift self-healing pipelines in **TalentScout**, or debugging kernel/driver failures with **WinDbg** symbol-connected stack traces, I eliminate root causes rather than padding timeouts.

I would welcome a technical conversation about the reliability bottlenecks, CI/CD velocity goals, or AI engineering workflows you are prioritizing at **{company}**.

Best regards,

**{name}**  
Principal QA Architect & Agentic AI Systems Engineer
""".strip()

    if norm_tone == "ceo":
        return f"""{header}
**Executive Leadership**  
**{company}**  

**RE: Accelerating Release Velocity & Product Reliability — {title}**

Dear {company} Leadership,

Every growing technology company hits the same inflection point: shipping faster starts colliding with production risk, and engineering teams lose weeks to manual regression or unreliable tooling. I am reaching out regarding the **{title}** opportunity because my 26-year track record is built on turning quality engineering from a release bottleneck into a measurable speed-to-market advantage.

Three outcomes illustrate how I operate as a force multiplier:
- **85% Manual Regression Reduction (Smartsheet):** Stepped into a zero-automation baseline and built a 1,500+ test automation framework that freed engineers to focus on high-value product delivery.
- **Org & Throughput Scaling (Placed Inc., OpenMarket & Xbox):** Built a QA organization from one tester to a full multi-platform team, cut Fortune 500 upgrade validation cycles in half at Apptio, and helped quadruple daily certification throughput at Xbox.
- **Practical AI Force-Multiplication (2025–2026):** Architected **SeikoClaw-Harness**, **OpenBrain**, and custom **MCP** tooling to make AI-assisted engineering predictable, verifiable, and safe—proving 100% defect containment across 12 dimensions in controlled A/B benchmarking rather than relying on AI hype.

With direct alignment to **{top_matched}**, I can step into **{company}** immediately, diagnose the highest-leverage quality and developer-velocity bottlenecks, and deliver durable systems that protect both customer trust and shipping cadence.

I would appreciate the opportunity to discuss how I can contribute to **{company}**'s roadmap.

Sincerely,

**{name}**  
Principal QA Architect & Agentic AI Systems Engineer
""".strip()

    # Default: jd_informed
    jd_alignment_block = ""
    if jd_highlights:
        bullet_lines = "\n".join(f"- **JD Focus:** *\"{h}\"*" for h in jd_highlights)
        jd_alignment_block = f"\nReviewing your job description, several priorities stood out immediately:\n{bullet_lines}\n"

    missing_bridge = ""
    if missing:
        missing_str = ", ".join(missing[:4])
        missing_bridge = (
            f" Where your stack extends into **{missing_str}**, my track record of rapid stack assimilation—"
            f"including mastering new enterprise API frameworks, AWS/Docker migrations, and authoring custom TypeScript/Python MCP servers and self-healing Playwright/ADB harnesses—"
            f"means I ramp to production contribution quickly."
        )

    return f"""{header}
**Hiring Team**  
**{company}**  

**RE: Application for {title}**

Dear Hiring Team at {company},

I am writing to apply for the **{title}** position at **{company}**. With 26+ years of software quality architecture across **Microsoft**, **Smartsheet**, **OpenMarket**, **NVIDIA**, and **Xbox**—combined with recent hands-on architecture of **agentic AI engineering harnesses, MCP servers, and deterministic AI evaluation gates**—my experience maps directly to your core requirements in **{top_matched}**.
{jd_alignment_block}
Here is how my production results align with what the **{title}** role demands:

- **Enterprise Test Automation at Scale (Smartsheet & OpenMarket):** Built Smartsheet's **Karate DSL** + **BrowserStack** automation suite from 0% to **85% manual regression coverage (1,500+ tests)**, and standardized reusable API contract testing templates across **AWS**, **Docker**, and **Terraform** microservice migrations at OpenMarket.
- **Frontier AI & Agentic Development (SeikoClaw / OpenBrain / TalentScout):** Architected **SeikoClaw-Harness** (130+ agent skills, 5-stage isolated spec reviews, and Anti-Soft-Pass verification gates), **OpenBrain** (SQLite + ChromaDB + SpacetimeDB semantic memory), **LocalMind** (self-healing `llama.cpp` GGUF inference), and **TalentScout** (stealth Playwright scraping with circuit breakers, DOM drift self-healing, and a 7-tool MCP server).
- **Deep Diagnostics & Cross-Platform Rigor (Microsoft, Placed Inc., Apptio):** Engineered WTT/PXE hardware lab automation, conducted white-box **WinDbg** stack trace analysis, built QA organizations from the ground up, and cut Fortune 500 regression cycles by 50%.

{missing_bridge.strip() if missing_bridge else f"I bring an adversarial quality mindset, clean documentation habits, and a bias for building reusable automation levers that accelerate the entire engineering team at {company}."}

Thank you for your time and consideration. I welcome the opportunity to discuss how my automation depth and AI-native quality workflows can immediately support **{company}**'s goals.

Sincerely,

**{name}**  
Principal QA Architect & Agentic AI Systems Engineer
""".strip()


def _add_formatted_runs(paragraph, text: str, base_size_pt: float = 10.0, base_color=(30, 41, 59)):
    """Parse lightweight markdown inline **bold**, *italic*, `code`, and [label](url) into python-docx runs."""
    from docx.shared import Pt, RGBColor

    # Convert markdown links [label](url) -> label (url) for clean ATS readability
    cleaned = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    tokens = re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)", cleaned)

    for tok in tokens:
        if not tok:
            continue
        bold = False
        italic = False
        font_name = "Arial"
        content = tok
        if tok.startswith("**") and tok.endswith("**") and len(tok) > 4:
            bold = True
            content = tok[2:-2]
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            italic = True
            content = tok[1:-1]
        elif tok.startswith("`") and tok.endswith("`") and len(tok) > 2:
            font_name = "Consolas"
            content = tok[1:-1]

        run = paragraph.add_run(content)
        run.bold = bold
        run.italic = italic
        run.font.name = font_name
        run.font.size = Pt(base_size_pt)
        run.font.color.rgb = RGBColor(*base_color)


def markdown_to_docx(markdown_text: str, output_path: str, doc_title: str = "") -> bool:
    """Convert tailored Markdown into a clean, ATS-safe Word (.docx) document."""
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn

        doc = Document()
        if doc_title:
            doc.core_properties.title = doc_title
        doc.core_properties.author = "Thomas S. Snyder"

        for section in doc.sections:
            section.top_margin = Inches(0.6)
            section.bottom_margin = Inches(0.6)
            section.left_margin = Inches(0.7)
            section.right_margin = Inches(0.7)

        normal_style = doc.styles["Normal"]
        normal_style.font.name = "Arial"
        normal_style.font.size = Pt(10)

        for raw_line in markdown_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("# "):
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(2)
                run = p.add_run(line[2:].strip())
                run.bold = True
                run.font.name = "Arial"
                run.font.size = Pt(18)
                run.font.color.rgb = RGBColor(15, 52, 96)
            elif line.startswith("## "):
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(10)
                p.paragraph_format.space_after = Pt(4)
                pPr = p._p.get_or_add_pPr()
                pBdr = OxmlElement("w:pBdr")
                bottom = OxmlElement("w:bottom")
                bottom.set(qn("w:val"), "single")
                bottom.set(qn("w:sz"), "6")
                bottom.set(qn("w:space"), "3")
                bottom.set(qn("w:color"), "CBD5E1")
                pBdr.append(bottom)
                pPr.append(pBdr)
                run = p.add_run(line[3:].strip().upper())
                run.bold = True
                run.font.name = "Arial"
                run.font.size = Pt(11)
                run.font.color.rgb = RGBColor(15, 52, 96)
            elif line.startswith("### "):
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(7)
                p.paragraph_format.space_after = Pt(2)
                run = p.add_run(line[4:].strip())
                run.bold = True
                run.font.name = "Arial"
                run.font.size = Pt(10.5)
                run.font.color.rgb = RGBColor(22, 33, 62)
            elif line.startswith("- ") or line.startswith("* "):
                p = doc.add_paragraph(style="List Bullet")
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(2.5)
                _add_formatted_runs(p, line[2:].strip(), base_size_pt=9.5)
            elif line.startswith("> "):
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Inches(0.25)
                p.paragraph_format.space_after = Pt(4)
                _add_formatted_runs(p, line[2:].strip(), base_size_pt=9.5, base_color=(71, 85, 105))
            else:
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(4)
                _add_formatted_runs(p, line, base_size_pt=10.0)

        doc.save(output_path)
        return True
    except Exception as e:
        print(f"DOCX export warning for {output_path}: {e}")
        return False


def _generate_ai_cover_letter(
    candidate: Dict[str, Any],
    job: Dict[str, Any],
    tone: str,
    signals: Dict[str, Any],
    provider: str,
    model: Optional[str],
    llm_cfg: Dict[str, Any],
) -> Optional[str]:
    """Use the configured LLM provider to craft an audience-specific cover letter grounded in resume.json."""
    company = job.get("company", "Company")
    title = job.get("title", "Senior QA Engineer")
    tone_meta = COVER_LETTER_TONE_META.get(tone, COVER_LETTER_TONE_META["jd_informed"])
    brief = _build_candidate_brief_for_llm(candidate, signals)

    audience_directives = {
        "jd_informed": (
            "Audience: Hiring Manager & Technical Panel (Job Description-Informed).\n"
            "Strategy: Mirror the exact requirements and terminology from the target role & Job Description. "
            "Map each priority requirement to a concrete fact-locked win from the candidate dossier (including both 26-year enterprise QA automation AND recent AI/Agentic Harness/MCP engineering). "
            "If unfamiliar/missing skills exist, bridge them credibly via transferable engineering wins."
        ),
        "hr": (
            "Audience: HR / Recruiter / Talent Acquisition.\n"
            "Strategy: Warm, energetic, and ultra-scannable (30-second skim). Open cleanly, include 4-5 crisp bullet points answering the recruiter checklist "
            "(26+ years experience, exact skill overlap, headline quantifiable metrics, AI/agentic readiness, Redmond WA / Remote availability), and avoid dense jargon walls."
        ),
        "cto": (
            "Audience: CTO / VP of Engineering / Principal Technical Leader.\n"
            "Strategy: Peer-to-peer technical systems voice. Cut fluff completely. Lead with architectural rigor: zero-to-one automation frameworks (1,500+ Karate tests / 85% coverage), "
            "kernel-to-cloud diagnostics (WinDbg, AWS microservices, MitM fault injection), native-protocol levers (Pure-ADB, Playwright DOM-drift self-healing), "
            "and production agentic AI systems (SeikoClaw-Harness, MCP servers, Anti-Soft-Pass verification gates, OpenBrain memory, self-healing LocalMind GGUF)."
        ),
        "ceo": (
            "Audience: CEO / Founder / Executive Leadership.\n"
            "Strategy: Crisp, strategic, business-outcome voice (~250-320 words). Frame everything in terms of ROI, speed-to-market, risk containment, org building (1 tester -> full QA team), "
            "85% manual regression elimination, and practical AI force-multiplication backed by empirical A/B benchmarking rather than hype."
        ),
    }

    jd_excerpt = signals.get("jd_text", "")[:2400]
    jd_block = f"\n### PASTED JOB DESCRIPTION:\n{jd_excerpt}\n" if jd_excerpt else ""

    prompt = f"""Write a polished, high-impact Cover Letter in clean Markdown for the candidate applying to this role.

### TARGET ROLE:
- Company: {company}
- Title: {title}
- Matched Skills: {json.dumps(signals.get('combined_keywords', []))}
- Unfamiliar / Missing Skills: {json.dumps(signals.get('missing_skills', []))}
{jd_block}
### AUDIENCE & TONE DIRECTIVE ({tone_meta['label']}):
{audience_directives.get(tone, audience_directives['jd_informed'])}

### FACT-LOCKED CANDIDATE DOSSIER (ONLY use facts, companies, projects, and metrics from below — NEVER fabricate):
{brief}

### RULES:
- Output ONLY the Cover Letter in clean Markdown (include candidate header, recipient block, subject line, body, and sign-off).
- Keep it concise, concrete, and completely free of generic AI cliches (no "delve", "tapestry", "thrilled to express", or empty buzzwords).
- Explicitly reference {company} and {title}.
"""
    try:
        resp = query_ai_service(
            messages=[
                {"role": "system", "content": "You are an executive technical career strategist writing sharp, authentic, fact-locked cover letters. Output Markdown only."},
                {"role": "user", "content": prompt},
            ],
            provider=provider,
            model=model,
            profile_llm_cfg=llm_cfg,
            max_tokens=1600,
        )
        if resp and not resp.startswith("Error:") and len(resp.strip()) >= 200 and company.lower() in resp.lower():
            return resp.strip()
    except Exception as e:
        print(f"AI cover letter generation ({tone}) failed: {e}")
    return None


def _generate_ai_executive_summary(
    candidate: Dict[str, Any],
    job: Dict[str, Any],
    signals: Dict[str, Any],
    provider: str,
    model: Optional[str],
    llm_cfg: Dict[str, Any],
) -> Optional[str]:
    """Generate a single sharp, job-tailored 3-4 sentence executive summary shared across all 7 ATS resume variants."""
    company = job.get("company", "Company")
    title = job.get("title", "Senior QA Engineer")
    brief = _build_candidate_brief_for_llm(candidate, signals)
    jd_excerpt = signals.get("jd_text", "")[:1800]
    jd_block = f"\nJob Description Excerpt:\n{jd_excerpt}\n" if jd_excerpt else ""

    prompt = f"""Write ONLY a 3-4 sentence targeted Professional Summary paragraph (no headings, no bullets) for Thomas S. Snyder applying to **{title}** at **{company}**.
Highlight matched skills ({', '.join(signals.get('combined_keywords', [])[:10])}), his 26+ years of enterprise QA automation (Smartsheet 0->85% / 1,500 Karate tests, OpenMarket AWS, Microsoft), AND his recent AI/agentic engineering advancements (SeikoClaw-Harness, MCP servers, deterministic AI evaluation gates, OpenBrain, LocalMind) as relevant.
{jd_block}
Fact-locked dossier:
{brief}
"""
    try:
        resp = query_ai_service(
            messages=[
                {"role": "system", "content": "Output a single crisp 3-4 sentence executive resume summary paragraph. No headers, no filler, strictly factual."},
                {"role": "user", "content": prompt},
            ],
            provider=provider,
            model=model,
            profile_llm_cfg=llm_cfg,
            max_tokens=350,
        )
        cleaned = (resp or "").strip().strip('"').strip()
        if cleaned and not cleaned.startswith("Error:") and 80 <= len(cleaned) <= 1200 and not cleaned.startswith("#"):
            return cleaned
    except Exception as e:
        print(f"AI summary generation failed: {e}")
    return None


def build_fallback_tailored_package(
    candidate: Dict[str, Any],
    job: Dict[str, Any],
    cover_letter_tone: str = "jd_informed",
    job_description: str = "",
) -> Dict[str, Any]:
    """Deterministic full package builder generating ALL 7 ATS resume styles and ALL 4 cover letter audiences."""
    signals = extract_jd_signals(job_description, job, candidate)
    resumes = {
        style: build_tailored_resume_md(candidate, job, style=style, signals=signals)
        for style in RESUME_STYLES
    }
    cover_letters = {
        tone: build_tailored_cover_letter_md(candidate, job, tone=tone, signals=signals)
        for tone in COVER_LETTER_TONES
    }
    active_tone = cover_letter_tone if cover_letter_tone in COVER_LETTER_TONES else "jd_informed"
    return {
        "resume_md": resumes["STANDARD"],
        "cover_letter_md": cover_letters[active_tone],
        "resumes": resumes,
        "cover_letters": cover_letters,
        "active_cover_tone": active_tone,
    }


def _resolve_job_out_dir(job: Dict[str, Any]) -> tuple[str, str]:
    company = job.get("company", "Company")
    title = job.get("title", "QA Engineer")
    folder_name = f"{sanitize_folder_name(company)}_{sanitize_folder_name(title)}"
    out_dir = os.path.join(TAILORED_DIR, folder_name)
    return folder_name, out_dir


def _list_package_files(out_dir: str) -> List[str]:
    if not os.path.isdir(out_dir):
        return []
    return sorted(
        f for f in os.listdir(out_dir)
        if os.path.isfile(os.path.join(out_dir, f)) and f.endswith((".md", ".docx", ".json"))
    )


def tailor_for_job(
    job_id: int,
    model_name: Optional[str] = None,
    provider: Optional[str] = None,
    cover_letter_tone: str = "jd_informed",
    job_description: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate ALL 7 ATS resume styles (Standard, CARL, CAR, STAR, LPS, ELITE, WHO)
    and ALL 4 cover letter target audiences (JD-Informed, HR, CTO, CEO) in both .md and .docx.
    """
    job = get_job_details(job_id)
    if not job:
        raise ValueError(f"Job with ID {job_id} not found.")

    active_tone = (cover_letter_tone or "jd_informed").lower()
    if active_tone not in COVER_LETTER_TONES:
        active_tone = "jd_informed"

    # Persist pasted job description to SQLite if provided
    effective_jd = (job_description if job_description is not None else (job.get("description") or "")).strip()
    if job_description is not None:
        from scripts.database import update_job_description
        update_job_description(job_id, effective_jd)
        job["description"] = effective_jd

    from scripts.profile import get_active_profile
    active_profile = get_active_profile()
    p_cfg = active_profile.get("config", {}) if active_profile else {}
    llm_cfg = p_cfg.get("llm", {})

    target_provider = (provider or llm_cfg.get("provider", "local")).lower()
    target_model = model_name or llm_cfg.get("model_name")

    candidate = get_candidate_data()
    company = job.get("company", "Company")
    title = job.get("title", "QA Engineer")
    folder_name, out_dir = _resolve_job_out_dir(job)
    os.makedirs(out_dir, exist_ok=True)

    # Only probe local LLM if already online (don't block/stall 10s if offline when deterministic engine is instant)
    llm_ready = target_provider != "local"
    if target_provider == "local":
        status = check_llm_status()
        llm_ready = bool(status.get("online"))

    signals = extract_jd_signals(effective_jd, job, candidate)
    used_ai = False
    ai_summary: Optional[str] = None
    ai_cover_for_active: Optional[str] = None

    if llm_ready:
        ai_summary = _generate_ai_executive_summary(candidate, job, signals, target_provider, target_model, llm_cfg)
        if ai_summary:
            ai_cover_for_active = _generate_ai_cover_letter(candidate, job, active_tone, signals, target_provider, target_model, llm_cfg)
            used_ai = True

    # 1. Build ALL 7 resume styles (.md + .docx) sharing the tailored executive summary
    resumes: Dict[str, str] = {}
    for style in RESUME_STYLES:
        md_content = build_tailored_resume_md(
            candidate,
            job,
            style=style,
            signals=signals,
            custom_summary=ai_summary,
        )
        resumes[style] = md_content
        meta = RESUME_STYLE_META[style]
        md_path = os.path.join(out_dir, meta["filename_md"])
        docx_path = os.path.join(out_dir, meta["filename_docx"])
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        markdown_to_docx(md_content, docx_path, doc_title=f"Thomas S. Snyder — {title} ({meta['label']})")

    # 2. Build ALL 4 cover letter audiences (.md + .docx) + primary Cover_Letter.md/.docx
    cover_letters: Dict[str, str] = {}
    for tone in COVER_LETTER_TONES:
        if tone == active_tone and ai_cover_for_active:
            cl_content = ai_cover_for_active
        else:
            cl_content = build_tailored_cover_letter_md(candidate, job, tone=tone, signals=signals)
        cover_letters[tone] = cl_content
        t_meta = COVER_LETTER_TONE_META[tone]
        cl_md_path = os.path.join(out_dir, t_meta["filename_md"])
        cl_docx_path = os.path.join(out_dir, t_meta["filename_docx"])
        with open(cl_md_path, "w", encoding="utf-8") as f:
            f.write(cl_content)
        markdown_to_docx(cl_content, cl_docx_path, doc_title=f"Thomas S. Snyder — Cover Letter ({t_meta['label']})")

    # Write canonical Cover_Letter.md & Cover_Letter.docx mirroring active_tone
    resume_path = os.path.join(out_dir, "Resume.md")
    cover_letter_path = os.path.join(out_dir, "Cover_Letter.md")
    cover_letter_docx_path = os.path.join(out_dir, "Cover_Letter.docx")
    with open(cover_letter_path, "w", encoding="utf-8") as f:
        f.write(cover_letters[active_tone])
    markdown_to_docx(cover_letters[active_tone], cover_letter_docx_path, doc_title=f"Thomas S. Snyder — Cover Letter for {company}")

    # Persist job_spec.json and tailor_manifest.json
    job_spec_path = os.path.join(out_dir, "job_spec.json")
    with open(job_spec_path, "w", encoding="utf-8") as f:
        json.dump(job, f, indent=2)

    files_list = _list_package_files(out_dir)
    manifest = {
        "job_id": job_id,
        "company": company,
        "title": title,
        "active_cover_tone": active_tone,
        "used_llm": used_ai,
        "provider": target_provider,
        "model": target_model,
        "job_description": effective_jd,
        "resume_styles": RESUME_STYLES,
        "cover_letter_tones": COVER_LETTER_TONES,
        "files": files_list,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(os.path.join(out_dir, "tailor_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return {
        "status": "success",
        "exists": True,
        "job_id": job_id,
        "company": company,
        "title": title,
        "folder": folder_name,
        "folder_path": out_dir,
        "resume_path": resume_path,
        "cover_letter_path": cover_letter_path,
        "resume_md": resumes["STANDARD"],
        "cover_letter_md": cover_letters[active_tone],
        "resumes": resumes,
        "cover_letters": cover_letters,
        "active_cover_tone": active_tone,
        "job_description": effective_jd,
        "files": files_list,
        "style_meta": RESUME_STYLE_META,
        "tone_meta": COVER_LETTER_TONE_META,
        "used_llm": used_ai,
        "provider": target_provider,
        "model": target_model,
    }


def regenerate_cover_letter(
    job_id: int,
    tone: str = "jd_informed",
    job_description: Optional[str] = None,
    model_name: Optional[str] = None,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Regenerate a single target-audience cover letter (optionally with an updated Job Description)."""
    job = get_job_details(job_id)
    if not job:
        raise ValueError(f"Job with ID {job_id} not found.")

    norm_tone = (tone or "jd_informed").lower()
    if norm_tone not in COVER_LETTER_TONES:
        raise ValueError(f"Invalid cover letter tone: {tone}. Must be one of {COVER_LETTER_TONES}")

    effective_jd = (job_description if job_description is not None else (job.get("description") or "")).strip()
    if job_description is not None:
        from scripts.database import update_job_description
        update_job_description(job_id, effective_jd)
        job["description"] = effective_jd

    folder_name, out_dir = _resolve_job_out_dir(job)
    # If package doesn't exist yet, build full package with this tone
    if not os.path.exists(os.path.join(out_dir, "Resume.md")):
        return tailor_for_job(
            job_id,
            model_name=model_name,
            provider=provider,
            cover_letter_tone=norm_tone,
            job_description=effective_jd,
        )

    from scripts.profile import get_active_profile
    active_profile = get_active_profile()
    p_cfg = active_profile.get("config", {}) if active_profile else {}
    llm_cfg = p_cfg.get("llm", {})
    target_provider = (provider or llm_cfg.get("provider", "local")).lower()
    target_model = model_name or llm_cfg.get("model_name")

    candidate = get_candidate_data()
    signals = extract_jd_signals(effective_jd, job, candidate)

    llm_ready = target_provider != "local"
    if target_provider == "local":
        llm_ready = bool(check_llm_status().get("online"))

    used_ai = False
    cl_content = None
    if llm_ready:
        cl_content = _generate_ai_cover_letter(candidate, job, norm_tone, signals, target_provider, target_model, llm_cfg)
        if cl_content:
            used_ai = True

    if not cl_content:
        cl_content = build_tailored_cover_letter_md(candidate, job, tone=norm_tone, signals=signals)

    t_meta = COVER_LETTER_TONE_META[norm_tone]
    with open(os.path.join(out_dir, t_meta["filename_md"]), "w", encoding="utf-8") as f:
        f.write(cl_content)
    markdown_to_docx(cl_content, os.path.join(out_dir, t_meta["filename_docx"]), doc_title=f"Thomas S. Snyder — Cover Letter ({t_meta['label']})")

    # Also update canonical Cover_Letter.md/.docx to the newly generated tone
    with open(os.path.join(out_dir, "Cover_Letter.md"), "w", encoding="utf-8") as f:
        f.write(cl_content)
    markdown_to_docx(cl_content, os.path.join(out_dir, "Cover_Letter.docx"), doc_title=f"Thomas S. Snyder — Cover Letter for {job.get('company', '')}")

    # Update manifest
    manifest_path = os.path.join(out_dir, "tailor_manifest.json")
    manifest = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            manifest = {}
    manifest.update({
        "active_cover_tone": norm_tone,
        "job_description": effective_jd,
        "used_llm": used_ai or manifest.get("used_llm", False),
        "files": _list_package_files(out_dir),
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    pkg = get_existing_tailored_package(job_id) or {}
    pkg["status"] = "success"
    pkg["regenerated_tone"] = norm_tone
    pkg["used_llm"] = used_ai
    return pkg


def get_tailored_file_path(job_id: int, filename: str) -> Optional[str]:
    """Safely resolve a generated file inside the job's tailored output directory (no path traversal)."""
    job = get_job_details(job_id)
    if not job:
        return None
    safe_name = os.path.basename(filename or "")
    if not safe_name or safe_name != filename or ".." in filename:
        return None
    _, out_dir = _resolve_job_out_dir(job)
    full_path = os.path.abspath(os.path.join(out_dir, safe_name))
    if not full_path.startswith(os.path.abspath(out_dir) + os.sep):
        return None
    return full_path if os.path.isfile(full_path) else None


def get_existing_tailored_package(job_id: int) -> Optional[Dict[str, Any]]:
    """Load an existing tailored package (all 7 resume styles + all 4 cover letter audiences)."""
    job = get_job_details(job_id)
    if not job:
        return None
    company = job.get("company", "Company")
    title = job.get("title", "QA Engineer")
    folder_name, out_dir = _resolve_job_out_dir(job)

    resume_path = os.path.join(out_dir, "Resume.md")
    cover_letter_path = os.path.join(out_dir, "Cover_Letter.md")

    if not (os.path.exists(resume_path) and os.path.exists(cover_letter_path)):
        return None

    manifest_path = os.path.join(out_dir, "tailor_manifest.json")
    manifest: Dict[str, Any] = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception:
            manifest = {}

    resumes: Dict[str, str] = {}
    for style in RESUME_STYLES:
        p = os.path.join(out_dir, RESUME_STYLE_META[style]["filename_md"])
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                resumes[style] = f.read()

    cover_letters: Dict[str, str] = {}
    for tone in COVER_LETTER_TONES:
        p = os.path.join(out_dir, COVER_LETTER_TONE_META[tone]["filename_md"])
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                cover_letters[tone] = f.read()

    with open(resume_path, "r", encoding="utf-8") as f:
        resume_md = f.read()
    with open(cover_letter_path, "r", encoding="utf-8") as f:
        cover_letter_md = f.read()

    # Backwards-compat for legacy folders created before multi-tone support
    if not cover_letters:
        cover_letters["jd_informed"] = cover_letter_md

    active_tone = manifest.get("active_cover_tone", "jd_informed")
    if active_tone not in cover_letters:
        active_tone = next(iter(cover_letters.keys()), "jd_informed")

    return {
        "exists": True,
        "job_id": job_id,
        "company": company,
        "title": title,
        "folder": folder_name,
        "folder_path": out_dir,
        "resume_md": resume_md,
        "cover_letter_md": cover_letters.get(active_tone, cover_letter_md),
        "resumes": resumes,
        "cover_letters": cover_letters,
        "active_cover_tone": active_tone,
        "job_description": manifest.get("job_description") or job.get("description") or "",
        "files": _list_package_files(out_dir),
        "style_meta": RESUME_STYLE_META,
        "tone_meta": COVER_LETTER_TONE_META,
        "used_llm": manifest.get("used_llm", False),
        "provider": manifest.get("provider", "local"),
        "model": manifest.get("model"),
    }


if __name__ == "__main__":
    print("Checking LLM Status:", check_llm_status())
    print("Available Models:", list_local_models())
