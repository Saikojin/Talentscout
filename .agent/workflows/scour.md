---
description: How to scour job boards for qualified roles
---

### Scouring Workflow

This workflow describes how to find and filter job opportunities using the TalentScout tools.

9. **Fetch Tracked Jobs**
    - Run the spreadsheet manager to get existing URLs:
      ```bash
      python scripts/spreadsheet_manager.py --fetch
      ```

10. **Iterate through Sites (NO SKIPS)**
    - Iterate through EVERY site listed in [job_search_sites.json](file:///d:/DevWorkspace/TalentScout/job_search_sites.json).
    - Do not skip any site unless it is physically inaccessible.
    - For each site:
        - Use the browser agent to navigate to the URL.
        - Search for the specified `search_terms` in the specified `locations`.
        - Apply the defined `filters`.

11. **Evaluate Job Descriptions**
    - For each interesting job found:
        - **Duplicate Check**: Check if the URL is already in the spreadsheet.
          ```bash
          python scripts/spreadsheet_manager.py --check <job_url>
          ```
        - If it is a duplicate, **discard it** and do not add it to the review list or dashboard.
        - If not a duplicate:
            - Extract the full job description text.
            - Run the filter script:
              ```bash
              python scripts/filter_skills.py <path_to_jd_temp_file> base_skillset.json
              ```
            - **Critical Check**: Analyze the job description for any technical requirements or tools NOT listed in `core_skills` in `base_skillset.json`.
            - If a "disqualified" skill is found (e.g., Python), skip the job.
            - If an "unfamiliar" skill is found, note it down for the user.

12. **Update Tracking & Review List**
    - If a job passes the filter:
        - Add it to [jobs_to_review.md](file:///d:/DevWorkspace/TalentScout/jobs_to_review.md).
        - Include the match score, missing/unfamiliar skills, and a link.
        - **Update Spreadsheet**: Use the browser agent to append the URL to Column A and today's date to Column B of the A job tracking sheet of your choice.

13. **Notify User**
    - Once the scour is complete, notify the user with a summary of findings and a link to the review file.