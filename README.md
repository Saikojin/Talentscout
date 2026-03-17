# TalentScout

TalentScout is an automated agentic job scraper that utilizes Playwright to find, filter, and track relevant job postings across multiple job boards. It leverages search selectors and filtering keywords to narrow down job descriptions to ones that match your exact skill set and saves you from applying to duplicates by storing them in a local SQLite database.

## Features

- **Multi-Site Scraping**: Scour multiple job boards by defining site selectors in a JSON file.
- **Skill Filtering**: Define your skills and disqualified keywords to automatically reject bad fits before you even see them.
- **Local Database Tracking**: Uses a local SQLite database (`job_tracker.db`) to log scraped jobs and prevent re-evaluating the same URL twice.
- **Dashboard Output**: Generates an integrated HTML dashboard and a Markdown list (`jobs_to_review.md`) of passing and failing jobs for easy review.

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
If you do not have a `base_skillset.json` configured, use the built-in Resume Parser tool to generate one dynamically from your resume:
```bash
python scripts/resume_server.py
```
Open your browser to `http://localhost:8000` to access the parser dashboard. Upload your resume (PDF, DOCX, TXT), verify the extracted text, tweak the drafted JSON on the right pane, and click "Save".

### 2. Run the Job Scraper
To start scoring and filtering jobs:
```bash
python scripts/auto_scour.py
```

Results will be saved to your local database, and visual summaries will be updated in `dashboard.html` and `jobs_to_review.md`.
