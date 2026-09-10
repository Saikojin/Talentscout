# Task Checklist: AI Service API Keys in Profiles

- [x] **Task 1: Extend Profile Config & Schema (`scripts/profile.py`)**
  - [x] Add `llm` block (`provider`, `model_name`, `custom_endpoint`, `api_keys`) to `default_config()`.
  - [x] Update `validate_config()` to safely merge and sanitize `api_keys` for Google Gemini, OpenAI, Anthropic, Groq, OpenRouter, and Custom endpoints.

- [x] **Task 2: Build Multi-Provider Tailoring Engine (`scripts/tailor_engine.py`)**
  - [x] Add API dispatchers for Google Gemini, OpenAI, Anthropic, Groq, OpenRouter, and Custom endpoints.
  - [x] Integrate active profile LLM configuration into `tailor_for_job()`.
  - [x] Support fallback to environment variables when profile keys are not explicitly set.

- [x] **Task 3: Update Profile Editor UI (`dashboard/profile_editor.html`)**
  - [x] Add "AI Model & Service API Keys" section to the profile editing view.
  - [x] Add provider dropdown and model name inputs.
  - [x] Add masked password inputs with show/hide password toggles for all major AI services.
  - [x] Connect form fields to save and load profile JSON.

- [x] **Task 4: Add Backend Test / Validation Route (`scripts/dashboard_server.py`)**
  - [x] Add `POST /api/profiles/{id}/test_llm` endpoint to test API key validity on demand.

- [x] **Task 5: Automated Testing & End-to-End Verification**
  - [x] Run automated tests for profile creation, key storage, and provider generation.
  - [x] Verify live in `dashboard/profile_editor.html`.
