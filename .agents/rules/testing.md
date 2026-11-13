# Verification rules

**When:** any behavior or contract change.

- Each change needs a test proportional to impact: unit, contract/mock,
  integration, and optional disposable-company E2E.
- Every public operation validates successful and failure responses,
  DTO fields, permission denial, pagination and retry/idempotency rules.
- Unit/mocked tests are not evidence that YouGile's live API accepts fields.
- CI must validate current contract records, inventory, lint/compile,
  unit tests and reproducible container build.
- Capture one failing regression test before fixing a reported bug when
  practical; avoid tests that only mirror the implementation.
- Do not update tests only to make a broken change look green.
- Never print or commit real API keys, production customer data, full response
  bodies or private company identifiers in test fixtures.
- Report actual test commands and outcomes; distinguish not-run from passing.
