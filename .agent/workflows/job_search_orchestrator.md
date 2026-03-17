# Orchestrator Workflow (Mission Control)

## Description
This workflow manages the end-to-end job search process, spawning sub-agents and handling user clarification loops.

## Phase 1: Initialization
1.  **Skill Map Creation**:
    - **Action**: Execute `python scripts/resume_parser.py "base_materials/Tester Resume All.docx"`
    - **Analysis**: Analyze the extracted text output to build the Skill Map.
    - Extract semantic skills, focusing on "20+ years of QA", "Leadership", and "Early AI adoption".
    - Store in memory or as a temporary artifact `logs/skill_map.json`.

## Phase 2: Agent Management Loop
1.  **Spawn: The Scourer**
    - **Target**: LinkedIn, Indeed, BuiltIn Seattle.
    - **Filter**: "Agentic AI", "QA Engineer", "Seattle/Redmond".
    - **Output**: List of Job Descriptions (JDs).
2.  **Spawn: The Evaluator** (Per JD)
    - **Check 1**: Salary $\ge$ 140k? (If unknown, check ambiguity rules).
    - **Check 2**: FTE?
    - **Check 3**: 60% Match? (Cross-reference Skill Map vs JD).
    - **Decision**: Pass / Fail / Ask User.
3.  **Spawn: The Tailor** (For Passing JDs)
    - **Action**: Create resume variation in `tailored_outputs/`.
    - **Action**: Write TEAR framework cover letter.


## Phase 3: Clarification Loop
The Orchestrator MUST pause and query the User (Thomas) via `notify_user` if:
1.  **Ambiguity**: JD is unclear on FTE status or Salary.
2.  **Skill Gap**: High-value role lists a critical required skill missing from the Skill Map.
3.  **Priority**: Multiple high-value roles found simultaneously.

## Phase 4: Application Submission
1.  **Spawn: The Applicant**
    - **Action**: Use browser to submit application.
    - **Artifact**: Capture screenshot of submission to `logs/`.

## Execution Trigger
- Run this workflow via the Agent Manager.
