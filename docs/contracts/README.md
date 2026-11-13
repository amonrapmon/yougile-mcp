# Durable contracts

This folder owns approved, observable requirements for the YouGile MCP.
It is intentionally separate from implementation plans, PR discussions and
temporary research notes.

## Format

Each record is one Markdown file named YC-NNN-<topic>.md and begins with:

---
id: YC-001
authority: current
owner: maintainer
applies_to: ["src/yougile_mcp/**", "catalog/**"]
superseded_by: null
---

Valid authority values:
- draft: not approved; visible for context, not implementation authority.
- current: explicitly approved by maintainer; governs matching files.
- archived: historical only; must name superseded_by (existing record ID).

A record has headings Intent, Invariants, Non-goals, Verification. Each
invariant should have a stable unique identifier such as YC-001/INV1.

## Working with the records

- python scripts/agent_contracts.py check
- python scripts/agent_contracts.py for src/yougile_mcp/config.py
- python scripts/agent_contracts.py diff origin/main

The router validates ID, authority, owner, path patterns and required
sections. It prints only CURRENT records as binding; drafts are listed
separately as warnings. It does not prove code meets every invariant.
Formal behavior needs appropriate program tests.

Changing a record's status to current requires explicit maintainer
approval; a merged PR or an existing code path is not implied approval.
All initial current records formalize decisions already made for this repo.

## Writing rubric

- State present observable behavior; do not narrate the PR or roadmap.
- Each record has one canonical owner and a narrow concern.
- Separate requirements from evidence and historical background.
- Explicitly list non-goals and externally visible failure behavior.
- Avoid tests that merely assert documentation text exists.
- Keep path selectors stable and avoid broad "**" selectors for narrow rules.
