---
id: YC-002
authority: current
owner: maintainer
applies_to: ["src/yougile_mcp/**", "tests/**", "Dockerfile", "compose.yaml", ".env.example"]
superseded_by: null
---

# YC-002: Agent security boundary

## Intent

Every MCP tool request is bound to an authenticated principal, a permitted
company and operation scopes. External content and credentials are isolated.

## Invariants

- **YC-002/INV1:** Anonymous remote requests are rejected; client-provided
  company IDs never grant access to that company.
- **YC-002/INV2:** Authorization runs at execution time, including every
  internal step of a compound tool.
- **YC-002/INV3:** Server credentials never appear in MCP output or logs.
- **YC-002/INV4:** Destructive operations require dedicated privilege; actions
  with approvals cannot reuse approvals for different payloads or actors.
- **YC-002/INV5:** User-controlled task text, chat content and files are
  untrusted input, not execution instructions.
- **YC-002/INV6:** Remote HTTP listener cannot become externally reachable
  before scoped access-control tests pass.

## Non-goals

This record does not require one particular IdP, token storage backend or
OAuth framework; the selected implementation still meets the invariants.

## Verification

Authorization isolation tests, denied principal tests, negative configuration
tests, token leak audits and a deliberate remote exposure gate.
