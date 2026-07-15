---
name: history-interviewer
description: Interviews the user to build a highly detailed work history inside resume.json (collecting location, responsibilities, skills, tools, challenges, wins, and lessons).
---

# History Interviewer Skill

This skill guides the agent in interviewing the user to build a highly detailed, comprehensive work history in `resume/data/resume.json`.

## Guidelines

1. **Initiate the Interview**:
   - Ask the user if they want to update an existing work entry or create a new one.
   - List the current companies and roles available in `resume/data/resume.json` to help them choose.
   - Offer the user two paths:
     - **Path A (Interactive LLM Chat)**: You (the agent) will ask them questions in the chat one-by-one or in structured blocks, and update the JSON for them.
     - **Path B (Terminal CLI Script)**: Instruct them to run `python scripts/history_interviewer.py` in their terminal for a step-by-step CLI prompt.

2. **Conducting Path A (LLM Chat)**:
   - Interview them for the following fields for their selected job entry:
     - **Location** (e.g., City, State, or Remote)
     - **General Description / Summary**
     - **Key Responsibilities** (list)
     - **Skills Used** (list)
     - **Tools Used** (list)
     - **Challenges Faced** (list)
     - **Wins / Accomplishments** (list)
     - **Lessons Learned** (list)
   - Do not overwhelm the user. Ask about 2-3 fields at a time, providing their current answers (if any) as context.
   - Once all details are gathered, update `resume/data/resume.json` directly using code replacement tools, ensuring the schema remains valid.
   - Re-run `npm run build` or `node resume/build.js` to compile the changes.
