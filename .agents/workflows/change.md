# Implementation workflow

1. Restate the user-visible goal, boundaries and relevant Linear issue.
2. Determine changed paths and run agent_contracts.py for each.
3. Read matching nested AGENTS.md, standing domain rules, and current records.
4. Search existing code, tests and active PRs to avoid duplicate solutions.
5. If the request changes an undecided public contract, follow decision.md
   before coding; if already decided, implement the narrowest compatible delta.
6. Write tests first for risky bugs and permission/compatibility boundaries.
7. Keep API operations centralized; include migration and rollback notes
   when behavior or persistence changes.
8. Run relevant checks and diff routes; review tool-visible data exposure.
9. Open a focused PR with evidence, contract IDs, test results and risks.
10. Report changes, actual validation and outstanding limitations. No
    invented success or silent background work.
