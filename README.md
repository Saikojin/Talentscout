# TalentScout

TalentScout is an automated agentic job scraper that utilizes Playwright to find, filter, and track relevant job postings across multiple job boards. It leverages search selectors and filtering keywords to narrow down job descriptions to ones that match your exact skill set and saves you from applying to duplicates by storing them in a local SQLite database.
> **Note:** The configuration files in this repository contain example data from the project creator. To use this scraper effectively, you must edit these configurations to suit your specific job requirements and selectors. Additionally, this project presumes the user has access to an AI assistant (or agent) to help automate actions beyond the code execution itself.

## Features

- **Multi-Site Scraping**: Scour multiple job boards by defining site selectors in a JSON file.
- **Skill Filtering**: Define your skills and disqualified keywords to automatically reject bad fits before you even see them.
- **Local Database Tracking**: Uses a local SQLite database (`job_tracker.db`) to log scraped jobs and prevent re-evaluating the same URL twice.
- **Dashboard Output & Scoring**: Generates an integrated HTML dashboard (`http://localhost:8088`) and a Markdown list (`jobs_to_review.md`) with multi-axis scoring.
- **1-Click Tailored Resume & Cover Letter Generator**: Generate targeted resumes and cover letters for specific job postings directly from the dashboard tiles.
- **Bundled Local LLM Engine (`llmworkbench/`)**: On-device AI inference using your own downloaded `.gguf` models with start/stop management directly in the UI.

## Tech Stack & Dependencies

- **Python 3.8+**: Core language for all scripts and logic.
- **Playwright** (`playwright`): Used for headless, Javascript-rendered, async web scraping.
- **FastAPI & Uvicorn** (`fastapi`, `uvicorn`, `python-multipart`): Powers the dashboard server (:8088) and local LLM backend (:8000).
- **LLMWorkbench Engine**: On-device GGUF model loader supporting Gemma, LFM, Qwen, etc.
- **BeautifulSoup4** (`beautifulsoup4`): HTML parsing for the visual learner tool.
- **PyPDF & python-docx** (`pypdf`, `python-docx`): Extracts raw text from uploaded resumes.
- **SQLite3**: Built-in Python library used for the local `job_tracker.db` deduplication database.
- **Vanilla HTML/CSS/JS**: Used for the dashboard rendering, avoiding the need for heavy node/npm dependencies.

## Setup

1. **Install Requirements**:
   Ensure you have Python 3.8+ installed, and run:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Download Local GGUF Models (Optional for Local AI)**:
   Place any GGUF language model (e.g. `gemma-3-1B-it-QAT-Q4_0.gguf`) into `llmworkbench/models/`.
   - *Note:* Models are excluded from git by default to keep the repository lightweight.
   - You can download models from [Hugging Face](https://huggingface.co/models?search=gguf).

3. **Configuration**:
   - `site_selectors.json`: Contains the CSS selectors and search URL templates for the job boards you want to scrape.
   - `job_search_sites.json`: Represents individual active queries (e.g., job title and location) you wish to apply on specific boards.
   - `base_skillset.example.json`: Rename this to `base_skillset.json` and fill it with your own personal skills. Jobs that don't match your criteria or contain disqualified skills will be automatically rejected.

## Usage

### 1. Start the Dashboard & Local LLM
Start the dashboard server:
```powershell
python scripts/dashboard_server.py
```
Open your browser to `http://localhost:8088`.
- In the top navigation, you will see the **Local LLM Widget**.
- Select a downloaded `.gguf` model from the dropdown and click **▶️ Start LLM**.

### 2. Run the Job Scraper
To start scoring and filtering jobs:
```bash
python scripts/auto_scour.py
```

### 3. Generate 1-Click Tailored Resumes & Cover Letters
In the Dashboard (`http://localhost:8088`):
1. Click **✨ Tailor Resume & Cover Letter** on any job tile.
2. The local LLM will synthesize a tailored resume with CAR/STAR bullet points and a matching cover letter.
3. The interactive viewer will pop open with 1-click **Copy to Clipboard** and saved files in `tailored_outputs/<Company_Role>/`.
