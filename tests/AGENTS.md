# Test-specific instructions

Inherits root AGENTS.md and CURRENT routed contracts. Read
.agents/rules/testing.md and .agents/rules/security.md when needed.

- Never use production keys, private task exports or live customer data.
- Unit tests must exercise actual behavior, not only the test's mocked
  expectations. Include denied/invalid paths for all security features.
- Live API E2E tests use a designated disposable company, explicit opt-in
  and documented isolation; skip automatically if opt-in is missing.
- Report not-run tests separately from tests that passed.
