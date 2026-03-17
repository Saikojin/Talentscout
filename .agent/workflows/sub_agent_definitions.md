# specialized Sub-Agent Modules

## 1. The Scourer (Market Intelligence)
- **Role**: Find potential job openings.
- **Tools**: Integrated Browser.
- **Sources**:
  - LinkedIn
  - Indeed
  - BuiltIn Seattle
- **Search Logic**:
  - Keywords: "Senior QA Engineer", "Agentic AI", "AI Quality".
  - Locations: "Redmond, WA", "Seattle, WA".
  - Companies: NVIDIA, Amazon, F5 Networks, Evertune AI.

## 2. The Evaluator (Match Verification)
- **Role**: Verify job fit against constraints.
- **Rules**:
  - **60% Rule**: Does the resume cover at least 60% of the JD requirements?
  - **Hard Gate**: Base Salary >= $140k.
  - **Hard Gate**: FTE Only.

## 3. The Tailor (Document Customization)
- **Role**: customize application materials.
- **Resume**: Adjust summary and highlights to match JD keywords (e.g., "AI Quality Architect" vs "Senior QA Lead").
- **Cover Letter**: Use **T.E.A.R. Framework**:
  - **T**ask: What was the challenge?
  - **E**nvironment: What tools/systems (AWS, Docker)?
  - **A**ction: What did you do (Leadership, Transformation)?
  - **R**esult: Quantifiable impact (e.g., "85% manual test reduction").

## 4. The Applicant (Execution)
- **Role**: Submit the application.
- **Tools**: Integrated Browser (Automated form filling).
- **Process**:
  - Fill entry fields.
  - Upload `tailored_outputs/[Specific Resume]`.
  - Upload `tailored_outputs/[Specific Cover Letter]`.
  - **Proof of Work**: Take screenshot of final "Submitted" screen.
  - Save screenshot to `logs/` with timestamp.
