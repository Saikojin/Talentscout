# TalentScout Manual Job Search Workflow

This guide details the steps to manually use the TalentScout system without relying on an LLM agent. By following this workflow, you can continuously discover, evaluate, and track job opportunities using the tools provided in the dashboard.

## Phase 1: Preparation & Configuration
Before starting the search, ensure your profile and target companies are up to date.

1. **Update Base Skillset**
   - Start the local servers using `start.bat`.
   - Open the **Resume Scanner** at `http://localhost:8000/`.
   - Upload your latest resume to parse the skills.
   - Review the extracted JSON and click "Save Skillset" to update the `base_skillset.json` file. This is crucial for accurate match scoring.

2. **Manage Job Sources & Companies**
   - Open the **Manage Crawlers** page at `http://localhost:8000/manage` or via the top navigation link.
   - **Sites Tab:** Add or update general job board configurations (e.g., search terms, CSS selectors).
   - **Companies Tab:** Add specific company career pages tracking the exact URLs and selectors to ensure we catch exclusive postings.

## Phase 2: Execution (Scouring for Jobs)
Run the automated scrapers to populate the database with new opportunities.

1. **Run Auto Scour**
   - Open a terminal and navigate to the project root directory.
   - Execute the crawling script manually: `python scripts/auto_scour.py`
   - **What it does:** The script reads configurations from `job_search_sites.json` and the database `search_configs`/`companies`. It will visit the sites, scrape new job listings, parse them, grade the required skills against your `base_skillset.json`, and insert the new entries into `job_tracker.db` with a computed match percentage.
   - *Tip*: Run this script daily or weekly to refresh the job pool.

## Phase 3: Review & Triage
Evaluate the accumulated jobs using the Dashboard.

1. **Open Dashboard**
   - Navigate to the **Dashboard** at `http://localhost:8001/`.
   - Click **Connect to Database**. This will fetch all jobs currently marked as `new`.

2. **Batch Rejection (Optional but Recommended)**
   - To quickly filter out highly unsuitable roles, use the **Reject Below %** feature.
   - Select your cutoff percentage from the dropdown (e.g., `20%`).
   - Click **Reject Below %**. The system will automatically mark all jobs below this threshold as `rejected` in the database, decluttering your view.

3. **Manual Evaluation**
   - Review each remaining job card. The card will display your **Match Score**, **Matched Skills**, and **Unfamiliar Skills / Focus**.
   - If a job looks promising, click **View Opportunity** to read the full description and apply.
   - **Actioning:** 
     - Check the **Applied To** box if you completed the application. This updates the database and removes the card.
     - Check the **Rejected** box if upon further inspection the role isn't a fit. This also removes the card.

## Summary
By maintaining an accurate skillset and list of target companies, running the `auto_scour.py` script regularly, and triaging via the Dashboard, you maintain a structured, manual pipeline for managing your job search.
