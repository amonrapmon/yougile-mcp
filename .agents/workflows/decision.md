# Durable decision workflow

Use this when stable API, security, ownership, data storage, compatibility or
observable behavior is not decided by a CURRENT contract.

1. Search current records with agent_contracts.py and check overlapping PRs.
2. Pick the existing canonical record owner when the concern fits; avoid a
   duplicate record merely because a new feature needs it.
3. Draft a docs/contracts/YC-NNN-*.md with authority: draft and applicable
   paths. Write observable behavior, invariants and verification criteria;
   explain rejected alternatives briefly. Do not mix implementation status
   into the specification.
4. Obtain explicit review/approval from the responsible maintainer before
   changing authority to current. A merged PR alone is not approval.
5. Implement/update runtime code and tests against the current record, then
   re-run contract validation and PR workflow.
6. When superseded, mark archived and reference the replacement record;
   do not delete prior decisions and do not use archived rules as authority.
