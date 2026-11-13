---
id: YC-005
authority: current
owner: maintainer
applies_to: ["AGENTS.md", "CLAUDE.md", ".agents/**", ".github/copilot-instructions.md", ".github/pull_request_template.md", "docs/contracts/**", "scripts/agent_contracts.py", "tests/test_agent_contracts.py"]
superseded_by: null
---

# YC-005: Agent development governance

## Intent

A single canonical entry point, nested instructions and current architecture
contracts guide every automated or human implementation in the same way.

## Invariants

- **YC-005/INV1:** Shared agent rules have one canonical home in AGENTS.md
  and .agents/rules/; tool-specific wrappers link to it without divergence.
- **YC-005/INV2:** Nested AGENTS.md files refine rules for their local paths
  but never weaken repo-wide licensing or security boundaries.
- **YC-005/INV3:** Only current, maintainer-approved records govern behavior.
  Draft and archived records cannot silently become implementation authority.
- **YC-005/INV4:** Agents can discover applicable current records by path and
  verify knowledge-record integrity without a service dependency.
- **YC-005/INV5:** Changes to a contract are reviewed with code, tests and
  source provenance when relevant; conflicting owners are resolved explicitly.

## Non-goals

Textual rule discovery does not replace technical enforcement and security
tests. CI verifies metadata structure but cannot automatically prove every
prose requirement.

## Verification

The stdlib contract router validates record metadata, path routes, archival
references and nested instructions. CI runs the router and its tests.
