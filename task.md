# Task Checklist: 1-Click Tailored Resume & Bundled Local LLM Engine

- [x] **Task 1: Package Bundled LLM Engine (`llmworkbench/`)**
  - [x] Bundle lightweight server scripts into `llmworkbench/main.py`.
  - [x] Create `llmworkbench/models/` directory with `.gitkeep` and `README.md`.
  - [x] Configure `.gitignore` to strictly exclude all `*.gguf`, `*.bin`, `*.safetensors` files.

- [x] **Task 2: Build Local LLM Bridge & Tailor Engine (`scripts/tailor_engine.py`)**
  - [x] Ingest candidate data from `resume/data/resume.json`.
  - [x] Extract job details and matched/missing skills from SQLite.
  - [x] Implement local LLM querying via OpenAI-compatible endpoint with automatic fallback.
  - [x] Write generated `Resume.md` and `Cover_Letter.md` to `tailored_outputs/<Company_Role>/`.

- [x] **Task 3: Implement Dashboard Server Endpoints (`scripts/dashboard_server.py`)**
  - [x] `GET /api/llm/status`: Status check and available models list.
  - [x] `POST /api/llm/start`: Start local model server.
  - [x] `POST /api/llm/stop`: Stop local model server.
  - [x] `POST /api/jobs/{job_id}/tailor`: Trigger resume and cover letter generation.
  - [x] `GET /api/jobs/{job_id}/tailor`: Retrieve existing generated packages.

- [x] **Task 4: Implement Dashboard UI Controls & Interactive Modal (`dashboard.html`)**
  - [x] Add top-navigation Local LLM status pill, model selector, and Start/Stop toggle buttons.
  - [x] Add `✨ Tailor Resume` button on every job card with loading state animations.
  - [x] Build dark-glass popup modal with tabs (Resume Preview, Cover Letter Preview, Details) and 1-click clipboard copying.

- [x] **Task 5: Documentation & Integration Testing**
  - [x] Update `README.md` and `CONTEXT.md` with instructions on local LLM setup.
  - [x] Write unit & integration test script `scripts/test_tailor.py`.
