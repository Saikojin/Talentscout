# TalentScout

TalentScout is an automated agentic job scraper that utilizes Playwright to find, filter, and track relevant job postings across multiple job boards. It leverages search selectors and filtering keywords to narrow down job descriptions to ones that match your exact skill set and saves you from applying to duplicates by storing them in a local SQLite database.
> **Note:** The configuration files in this repository contain example data from the project creator. To use this scraper effectively, you must edit these configurations to suit your specific job requirements and selectors. Additionally, this project presumes the user has access to an AI assistant (or agent) to help automate actions beyond the code execution itself.

## Features

- **Multi-Site Scraping**: Scour multiple job boards by defining site selectors in a JSON file.
- **Skill Filtering**: Define your skills and disqualified keywords to automatically reject bad fits before you even see them.
- **Local Database Tracking**: Uses a local SQLite database (`job_tracker.db`) to log scraped jobs and prevent re-evaluating the same URL twice.
- **Dashboard Output**: Generates an integrated HTML dashboard and a Markdown list (`jobs_to_review.md`) of passing and failing jobs for easy review.

## Tech Stack & Dependencies

- **Python 3.8+**: Core language for all scripts and logic.
- **Playwright** (`playwright`): Used for headless, Javascript-rendered, async web scraping.
- **FastAPI & Uvicorn** (`fastapi`, `uvicorn`, `python-multipart`): Powers the local web server endpoint for the resume parser UI.
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

2. **Configuration**:
   - `site_selectors.json`: Contains the CSS selectors and search URL templates for the job boards you want to scrape.
   - `job_search_sites.json`: Represents individual active queries (e.g., job title and location) you wish to apply on specific boards.
   - `base_skillset.example.json`: Rename this to `base_skillset.json` and fill it with your own personal skills. Jobs that don't match your criteria or contain disqualified skills will be automatically rejected.

## Usage

### 1. Generate `base_skillset.json`
If you do not have a `base_skillset.json` configured, use the built-in Resume Parser tool to generate one dynamically from your resume. 

Start the server using the provided batch script:
```bash
.\start.bat
```
Open your browser to `http://localhost:8000` to access the parser dashboard. Upload your resume (PDF, DOCX, TXT), verify the extracted text, tweak the drafted JSON on the right pane, and click "Save".

When you're finished, you can stop the background server using:
```bash
.\stop.bat
```

### 2. Run the Job Scraper
To start scoring and filtering jobs:
```bash
python scripts/auto_scour.py
```

Results will be saved to your local database, and visual summaries will be updated in `dashboard.html` and `jobs_to_review.md`.
