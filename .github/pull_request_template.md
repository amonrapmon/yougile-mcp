## Summary

## Related Linear issue
- GEN-___

## Applicable current contracts

- Contract IDs (from `python scripts/agent_contracts.py diff origin/main`):
- New / changed decision (if any):
- Decision approval or unresolved owner:

## Evidence and risks

- Executed checks (pass/fail/not run):
- Permission, data and side-effect impact:
- Migration/rollback (if applicable):

## Checklist
- [ ] No secrets, private data, credentials or copied unlicensed source
- [ ] Imported third-party code documented in NOTICE and docs/PROVENANCE.md
- [ ] Nested AGENTS.md and CURRENT path-matched contracts reviewed
- [ ] `python scripts/agent_contracts.py check` passes
- [ ] Tests added or adapted; CI passes
- [ ] API changes reviewed against YouGile OpenAPI and checked for pagination
- [ ] Authorization enforced by the executor (including smart tools)
- [ ] Writes have safe retry and idempotency policies
- [ ] Documentation / .env.example updated for new settings
