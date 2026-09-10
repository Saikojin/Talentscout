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

def build_fallback_tailored_package(candidate: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, str]:
    """Deterministic fallback tailoring if LLM is offline or model generation fails."""
    company = job.get("company", "the company")
    title = job.get("title", "QA Engineer")
    matched = job.get("matched_skills", [])
    basics = candidate.get("basics", {})
    work = candidate.get("work", [])
    
    matched_str = ", ".join(matched) if matched else "Test Automation, API Testing, and Quality Engineering"

    # Fallback Resume
    resume_md = f"""# {basics.get('name', 'Thomas S. Snyder')}
**{title} — Tailored for {company}**
{basics.get('email', '')} · {basics.get('location', {}).get('city', 'Redmond')}, {basics.get('location', {}).get('region', 'WA')} · [LinkedIn]({basics.get('url', '')})

## Professional Summary
Senior Software Test Engineer with 25+ years of experience across enterprise SaaS, cloud APIs, and hardware ecosystems. Targeted for the **{title}** role at **{company}**, bringing proven expertise in {matched_str}. Track record of building automated test suites from scratch and reducing manual regression by 85%.

## Core Competencies
- **Matched Target Skills:** {matched_str}
- **Frameworks & Tools:** Karate DSL, Postman, Playwright, Browserstack, Jira, Git, Docker, AWS
- **Methodologies:** CAR/STAR Automated Validation, Exploratory Testing, Test Planning, Defect Lifecycle

## Targeted Professional Experience
"""
    for job_entry in work[:4]:
        pos = job_entry.get("position", "")
        co = job_entry.get("name", "")
        start = job_entry.get("startDate", "")[:4]
        end = job_entry.get("endDate", "Present")
        end = end[:4] if end else "Present"
        resume_md += f"\n### {pos} · {co} ({start} – {end})\n"
        for w in job_entry.get("wins", job_entry.get("highlights", []))[:3]:
            resume_md += f"- **Impact:** {w}\n"

    # Fallback Cover Letter
    cover_letter_md = f"""# Thomas S. Snyder
Redmond, WA · {basics.get('email', 'Mr.Thomas.Snyder@gmail.com')}

**Hiring Team**  
**{company}**  

**RE: Application for {title}**

Dear Hiring Team at {company},

I am writing to express my strong enthusiasm for the **{title}** position at **{company}**. With over 25 years of quality engineering experience—ranging from building zero-baseline automated API test suites at Smartsheet to validating pre-release operating system builds at Microsoft—I am confident in my ability to elevate test coverage and accelerate release velocity for your team.

My background aligns directly with the requirements for this role, specifically in **{matched_str}**. At **Smartsheet**, I spearheaded the architecture of our Karate test automation suites from the ground up, covering 85% of all manual testing across 1,500+ automated test cases. At **OpenMarket**, I designed reusable API testing frameworks for high-volume SMS/MMS microservices transitioning to AWS cloud infrastructure.

What excites me most about {company} is the opportunity to solve complex quality challenges with rigor and speed. I bring an adversarial testing mindset, deep diagnostics capabilities (including white-box crash analysis and MitM proxy manipulation), and a commitment to clear cross-functional communication.

Thank you for your time and consideration. I welcome the opportunity to discuss how my automation experience and testing discipline can support {company}'s goals.

Sincerely,

**Thomas S. Snyder**  
Senior QA Engineer
"""
    return {"resume_md": resume_md.strip(), "cover_letter_md": cover_letter_md.strip()}

def tailor_for_job(job_id: int, model_name: Optional[str] = None, provider: Optional[str] = None) -> Dict[str, Any]:
    """Generate tailored Resume.md and Cover_Letter.md for a given job_id using active profile AI settings."""
    job = get_job_details(job_id)
    if not job:
        raise ValueError(f"Job with ID {job_id} not found.")

    from scripts.profile import get_active_profile
    active_profile = get_active_profile()
    p_cfg = active_profile.get("config", {}) if active_profile else {}
    llm_cfg = p_cfg.get("llm", {})

    target_provider = (provider or llm_cfg.get("provider", "local")).lower()
    target_model = model_name or llm_cfg.get("model_name")

    candidate = get_candidate_data()
    company = job.get("company", "Company")
    title = job.get("title", "QA Engineer")
    folder_name = f"{sanitize_folder_name(company)}_{sanitize_folder_name(title)}"
    out_dir = os.path.join(TAILORED_DIR, folder_name)
    os.makedirs(out_dir, exist_ok=True)

    # If local provider selected, ensure local server is up
    if target_provider == "local":
        status = check_llm_status()
        if not status.get("online"):
            print("Local LLM is offline. Attempting auto-start...")
            start_llm_server(target_model)
            time.sleep(2)

    resume_md = ""
    cover_letter_md = ""
    used_ai = False

    prompt = f"""You are an expert executive resume writer and career strategist.
Create a targeted, high-impact Resume and Cover Letter for the candidate applying to this specific role.

### TARGET JOB:
- Company: {company}
- Title: {title}
- Matched Skills: {json.dumps(job.get('matched_skills', []))}
- Unfamiliar / Missing Skills to address or de-emphasize: {json.dumps(job.get('missing_skills', []))}

### CANDIDATE PROFILE:
- Name: {candidate.get('basics', {}).get('name', 'Thomas S. Snyder')}
- Current Title: {candidate.get('basics', {}).get('label', 'Senior QA Engineer')}
- Core Career Highlights:
  1. Smartsheet (2021-2025): Built Karate automation suite from 0% to 85% coverage with 1,500 tests across web & Drupal.
  2. OpenMarket (2019-2021): Standardized Karate & Fit API testing for SMS/MMS/RCS microservices on AWS cloud.
  3. Apptio (2018): Created cheat sheets and streamlined data migration testing for Fortune 500 upgrades, cutting regression time in half.
  4. Placed Inc (2015-2018): Built QA department from 1 tester to full team; Web, iOS, Android, MitM proxy testing.
  5. Microsoft (2005-2014 across teams): Pre-release ARM & Windows compatibility, WTT automation, WinDbg debugging, Office Mobile scenario tests.
  6. VMC / Xbox (2001-2005): TCR compliance, pioneered 'Rabbit' end-to-end game completion test method, doubled team output.
- Tools: Karate DSL, Playwright, Browserstack, Postman, AWS, Docker, WinDbg, MitM Proxies, Jira, Git.

### FORMAT INSTRUCTIONS:
Produce TWO clean markdown sections separated by the exact delimiter `===SPLIT_COVER_LETTER===`:

[RESUME MARKDOWN SECTION]
Include:
- Header with contact info
- Targeted Professional Summary (3-4 sentences highlighting match to {company})
- Core Skills matrix (aligned to {job.get('matched_skills', [])})
- 4 Top Experience Entries with impactful bullet points (Action + Metric / Win)
- Education & Selected Projects

===SPLIT_COVER_LETTER===

[COVER LETTER MARKDOWN SECTION]
Write a polished, 3-4 paragraph tailored Cover Letter to the Hiring Team at {company} explaining why the candidate's specific background (especially Karate automation and hardware/device testing) makes them the ideal candidate for the {title} position.
"""
    try:
        raw_response = query_ai_service(
            messages=[
                {"role": "system", "content": "You are a professional technical resume and cover letter tailoring assistant. Output markdown only."},
                {"role": "user", "content": prompt}
            ],
            provider=target_provider,
            model=target_model,
            profile_llm_cfg=llm_cfg,
            max_tokens=2500
        )

        if raw_response and not raw_response.startswith("Error:") and len(raw_response) > 200:
            if "===SPLIT_COVER_LETTER===" in raw_response:
                parts = raw_response.split("===SPLIT_COVER_LETTER===")
                resume_md = parts[0].strip()
                cover_letter_md = parts[1].strip()
            else:
                resume_md = raw_response.strip()
            used_ai = True
        else:
            print(f"AI service returned non-standard output or error: {raw_response[:80]}... Using structured fallback.")
    except Exception as e:
        print(f"AI generation encountered error: {e}. Using structured fallback template.")

    # If AI generation was empty or failed, use fallback
    fallback = build_fallback_tailored_package(candidate, job)
    if not resume_md or len(resume_md) < 100:
        resume_md = fallback["resume_md"]
    if not cover_letter_md or len(cover_letter_md) < 100:
        cover_letter_md = fallback["cover_letter_md"]

    # Write files to output folder
    resume_path = os.path.join(out_dir, "Resume.md")
    cover_letter_path = os.path.join(out_dir, "Cover_Letter.md")
    job_spec_path = os.path.join(out_dir, "job_spec.json")

    with open(resume_path, "w", encoding="utf-8") as f:
        f.write(resume_md)
    with open(cover_letter_path, "w", encoding="utf-8") as f:
        f.write(cover_letter_md)
    with open(job_spec_path, "w", encoding="utf-8") as f:
        json.dump(job, f, indent=2)

    return {
        "status": "success",
        "job_id": job_id,
        "company": company,
        "title": title,
        "folder": folder_name,
        "folder_path": out_dir,
        "resume_path": resume_path,
        "cover_letter_path": cover_letter_path,
        "resume_md": resume_md,
        "cover_letter_md": cover_letter_md,
        "used_llm": used_ai,
        "provider": target_provider,
        "model": target_model
    }

def get_existing_tailored_package(job_id: int) -> Optional[Dict[str, Any]]:
    """Check if tailored files already exist for a job_id."""
    job = get_job_details(job_id)
    if not job:
        return None
    company = job.get("company", "Company")
    title = job.get("title", "QA Engineer")
    folder_name = f"{sanitize_folder_name(company)}_{sanitize_folder_name(title)}"
    out_dir = os.path.join(TAILORED_DIR, folder_name)
    
    resume_path = os.path.join(out_dir, "Resume.md")
    cover_letter_path = os.path.join(out_dir, "Cover_Letter.md")

    if os.path.exists(resume_path) and os.path.exists(cover_letter_path):
        with open(resume_path, "r", encoding="utf-8") as f:
            resume_md = f.read()
        with open(cover_letter_path, "r", encoding="utf-8") as f:
            cover_letter_md = f.read()
        return {
            "exists": True,
            "job_id": job_id,
            "company": company,
            "title": title,
            "folder": folder_name,
            "folder_path": out_dir,
            "resume_md": resume_md,
            "cover_letter_md": cover_letter_md
        }
    return None

if __name__ == "__main__":
    print("Checking LLM Status:", check_llm_status())
    print("Available Models:", list_local_models())
