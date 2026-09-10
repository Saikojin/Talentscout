from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from contextlib import asynccontextmanager
import os
import sys
import logging
from collections import deque
import time

# Ensure LocalMind is importable from sibling workspace or python path
localmind_src = r"D:\DevWorkspace\LocalMind\src"
if os.path.exists(localmind_src) and localmind_src not in sys.path:
    sys.path.insert(0, localmind_src)

try:
    from localmind.engine import LocalMindEngine
    from localmind.discovery import ModelDiscovery
except ImportError:
    LocalMindEngine = None
    ModelDiscovery = None

# --- Log Capture Setup ---
class LogBufferHandler(logging.Handler):
    def __init__(self, buffer):
        super().__init__()
        self.buffer = buffer

    def emit(self, record):
        msg = self.format(record)
        self.buffer.append(msg)

log_buffer = deque(maxlen=100)
buffer_handler = LogBufferHandler(log_buffer)
buffer_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

logging.getLogger().addHandler(buffer_handler)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model directories: local bundled models directory + fallback to external LLMWorkbench folder
MODEL_DIRS = [
    os.path.join(os.path.dirname(__file__), "models"),
    r"D:\DevWorkspace\LLMWorkbench\backend\models"
]
MODEL_DIR = MODEL_DIRS[0]
os.makedirs(MODEL_DIR, exist_ok=True)

def find_model_file(model_name: str) -> Optional[str]:
    """Search for a model filename across all configured model directories."""
    filename = model_name if model_name.endswith(".gguf") else f"{model_name}.gguf"
    for d in MODEL_DIRS:
        if os.path.exists(d):
            p = os.path.join(d, filename)
            if os.path.exists(p):
                return p
    return None

def get_all_available_models() -> List[str]:
    """List all available .gguf model filenames across search paths."""
    found = set()
    for d in MODEL_DIRS:
        if os.path.exists(d):
            for f in os.listdir(d):
                if f.endswith(".gguf"):
                    found.add(f)
    return sorted(list(found))

if LocalMindEngine:
    primary_dir = MODEL_DIRS[0] if (os.path.exists(MODEL_DIRS[0]) and any(f.endswith('.gguf') for f in os.listdir(MODEL_DIRS[0]))) else MODEL_DIRS[1]
    engine = LocalMindEngine(model_dir=primary_dir, backend="auto")
    discovery = ModelDiscovery(primary_dir)
else:
    engine = None
    discovery = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: parse model from args or environment
    model_name = os.environ.get("DEFAULT_MODEL")
    if not model_name:
        for i, arg in enumerate(sys.argv):
            if arg.startswith("--model="):
                model_name = arg.split("=", 1)[1]
            elif arg == "--model" and i + 1 < len(sys.argv):
                model_name = sys.argv[i + 1]
    
    if not model_name:
        available = get_all_available_models()
        preferred = [
            "gemma-3-1B-it-QAT-Q4_0.gguf",
            "Hunyuan-0.5B-Instruct_Q2_K.gguf",
            "LFM2.5-1.2B-Thinking-Q4_0.gguf",
            "Nebulos-Distill-Qwen3-0.6B.gguf"
        ]
        for pref in preferred:
            if pref in available:
                model_name = pref
                break
        if not model_name and available:
            valid = [f for f in available if not f.startswith("acestep-")]
            model_name = valid[0] if valid else available[0]
            
    if model_name and engine:
        model_path = find_model_file(model_name)
        if model_path and os.path.exists(model_path):
            logger.info(f"Startup: loading pre-specified model: {model_name} from {model_path}")
            engine.active_model_path = model_path
            engine.active_model_name = model_name
            engine.backend_type = "gguf"
            engine.mock_mode = False
            engine.reset_context()
        else:
            logger.error(f"Startup: pre-specified model file not found: {model_name}")
    yield
    # Shutdown
    if engine:
        logger.info("Lifespan shutdown triggered. Cleaning up workers...")
        engine.shutdown()

app = FastAPI(title="LLMWorkbench API", lifespan=lifespan)

# CORS for Dashboard UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    prompt: str
    max_tokens: int = 1024
    temperature: float = 0.7
    stop: Optional[List[str]] = None

class ModelLoadRequest(BaseModel):
    model_name: str

class DiscoveryRequest(BaseModel):
    url: str

class SettingsRequest(BaseModel):
    force_cpu: bool

# --- OpenAI Compatibility Layer ---
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: int = 1024
    stream: bool = False
    stop: Optional[List[str]] = None

class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str

class ChatCompletionUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage

def format_prompt(messages: List[ChatMessage]) -> str:
    prompt = ""
    for msg in messages:
        role = msg.role
        content = msg.content
        if role == "system":
            prompt += f"<|im_start|>system\n{content}\n<|im_end|>\n"
        elif role == "user":
            prompt += f"<|im_start|>user\n{content}\n<|im_end|>\n"
        elif role == "assistant":
            prompt += f"<|im_start|>assistant\n{content}\n<|im_end|>\n"
    if not prompt.endswith("<|im_start|>assistant\n"):
        prompt += "<|im_start|>assistant\n"
    return prompt

@app.get("/v1/models")
async def v1_list_models():
    models_list = []
    files = get_all_available_models()
    for f in files:
        models_list.append({
            "id": f,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "local"
        })
    return {"object": "list", "data": models_list}

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def v1_chat(req: ChatCompletionRequest):
    if not engine:
        raise HTTPException(status_code=500, detail="LocalMindEngine is not initialized on this system.")

    if req.model and req.model != engine.active_model_name:
        model_path = find_model_file(req.model)
        if model_path and os.path.exists(model_path):
            logger.info(f"Auto-loading model for v1/chat/completions: {req.model}")
            engine.active_model_path = model_path
            engine.active_model_name = req.model
            engine.backend_type = "gguf"
            engine.reset_context()
        else:
            logger.warning(f"Requested model {req.model} not found locally, using active: {engine.active_model_name}")
            
    if not engine.active_model_name:
        files = get_all_available_models()
        if files:
            model_name = files[0]
            model_path = find_model_file(model_name)
            logger.info(f"No active model. Auto-loading: {model_name}")
            engine.active_model_path = model_path
            engine.active_model_name = model_name
            engine.backend_type = "gguf"
            engine.reset_context()
        else:
            raise HTTPException(status_code=400, detail="No GGUF models available in models directory")

    prompt = format_prompt(req.messages)
    try:
        response = engine.generate(
            prompt=prompt,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            stop=req.stop or ["<|im_end|>", "<|im_start|>"]
        )
        
        prompt_tokens = len(prompt.split())
        completion_tokens = len(response.split())
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{int(time.time())}",
            created=int(time.time()),
            model=engine.active_model_name or "local",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=response),
                    finish_reason="stop"
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )
        )
    except Exception as e:
        logger.error(f"v1 chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
async def get_status():
    if not engine:
        return {"backend": "offline", "active_model": None, "is_loading": False}
    return {
        "backend": engine.backend_type,
        "active_model": engine.active_model_name,
        "is_loading": engine.is_loading,
        "mock_mode": engine.mock_mode,
        "force_cpu": engine.force_cpu,
        "capabilities": engine.capabilities
    }

@app.get("/api/models")
async def list_models():
    return {"models": get_all_available_models()}

@app.post("/api/load")
async def load_model(req: ModelLoadRequest):
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not available")
    model_path = find_model_file(req.model_name)
    if not model_path or not os.path.exists(model_path):
        raise HTTPException(status_code=404, detail="Model file not found")
    
    logger.info(f"Loading selected model: {req.model_name}")
    engine.active_model_path = model_path
    engine.active_model_name = req.model_name
    engine.backend_type = "gguf"
    engine.reset_context()
    return {"status": "loaded", "model": req.model_name}

@app.get("/api/logs")
async def get_logs():
    return {"logs": list(log_buffer)}

@app.post("/api/chat")
async def chat(req: ChatRequest):
    if not engine:
        raise HTTPException(status_code=500, detail="Engine not available")
    try:
        response = engine.generate(
            prompt=req.prompt,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            stop=req.stop
        )
        return {"text": response}
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reset")
async def reset_engine():
    if engine:
        engine.reset_context()
    return {"status": "reset"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
