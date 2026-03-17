# Search Constraints & Rules of Engagement

## 1. Compensation Filter
- **Minimum Base Salary**: $\ge \$140,000$ USD.
- **Strict Adherence**: Roles below this threshold must be automatically rejected unless there is explicit ambiguity that warrants User clarification.

## 2. Employment Type
- **Allowed**: Permanent Full-Time (FTE) ONLY.
- **Excluded**: "Contract", "Contractor", "Temporary", "Part-time".
- **Keywords to Avoid**: "C2C", "1099", "6-month contract".

## 3. Truthfulness Protocol
- **Rephrasing**: Sub-agents match keywords by rephrasing existing experience (e.g., "Manual Testing" -> "Human-in-the-loop Validation").
- **Prohibitions**: Strictly PROHIBITED from adding skills not supported by the master resume.
    - **Examples of Prohibited additions**: Karate, API Testing, AWS, Machine Learning, PMI training (unless verified in master resume).
    - **Note**: The prompt explicitly listed "Karate, API Testing, AWS..." as "Prohibited from adding... not supported by master resume". However, later in the document, it lists "Karate, Cypress, API Testing" as "Core Keywords (Truthful)".
    - **Conflict Resolution**: The "Truthful Keywords" section implies these specific skills *are* truthful for this user. The prohibition is against adding *unsupported* skills. If the user *has* these skills (as implied by Section 4), they can be used. If the user *does not*, they cannot.
    - **Safe Rule**: Only use keywords present in or semantically equivalent to the Master Resume content.

## 4. Geographic Priority
- **Primary Region**: Seattle and Redmond corridor.
- **Target Companies**: NVIDIA, Amazon, F5 Networks, Evertune AI.
