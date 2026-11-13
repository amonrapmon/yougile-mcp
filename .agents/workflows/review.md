# Pull request / review workflow

- Check the PR has one primary intent and a linked Linear issue.
- List changed paths; run agent_contracts.py diff <base> and read every
  current record it routes. Also read nested AGENTS.md for changed paths.
- Identify modified public contracts, permissions, secret/data exposure,
  idempotency, pagination, and external side effects.
- Check dependency licenses and third-party provenance; update NOTICE.
- Validate test claims using actual CI logs, not a checkbox or self-report.
- Run agent_contracts.py check, catalog check, unit tests, lint, compile
  and Docker verification where affected.
- Confirm no unrelated files, private data, release credentials, production
  task exports or local machine artifacts are in the diff.
- Report results: scope, applicable record IDs, pass/fail/not-run per command,
  risk, migration/rollback, and remaining blockers.
- Re-review after significant changes; never merge on a stale approval.
