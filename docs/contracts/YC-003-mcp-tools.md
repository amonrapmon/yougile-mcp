---
id: YC-003
authority: current
owner: maintainer
applies_to: ["src/yougile_mcp/**", "catalog/**", "tests/**"]
superseded_by: null
---

# YC-003: MCP tools and functional parity

## Intent

Direct and high-level MCP tools expose the complete supported YouGile API
without losing user workflows or mixing security models.

## Invariants

- **YC-003/INV1:** Low-level tools cover every supported REST operation or
  record the reason an endpoint cannot be exposed.
- **YC-003/INV2:** The 75 registered PR #5 tool names are historical functional
  targets, not evidence that any particular tool is implemented.
- **YC-003/INV3:** Each tool exposes stable, validated input and output schemas,
  scopes, side-effect classification, bounded output and errors.
- **YC-003/INV4:** Smart tools reuse direct API implementations and enforce
  equivalent policy and audit controls for every internal action.
- **YC-003/INV5:** Changes to public tool names, schemas, defaults or write
  behavior require a recorded compatibility decision and regression tests.

## Non-goals

Tool names are not required to match one REST operation each. Smart tools may
orchestrate several operations safely.

## Verification

Catalog-to-tool comparison, test discovery, capability-specific schema tests,
denied-scope tests and end-to-end workflows on disposable company data.
