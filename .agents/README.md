# Agent governance

Use AGENTS.md as the repository-wide entry point; these directories contain
domain rules, workflows, and optional task-specific skills.

- rules/: standing cross-cutting constraints, linked by AGENTS.md.
- workflows/: actionable change/decision/review checklists.
- skills/: task-specific recipes, not automatically binding for all work.
- docs/contracts/: current authoritative *observable* behavior and invariants.
- scripts/agent_contracts.py: validation and path-based routing.

Precedence: external/platform restrictions > root repository safeguards >
path-specific AGENTS.md and applicable current contracts > task-local planning.
A narrower document can refine but cannot relax repository-wide safety rules.

A tool-specific wrapper must point to AGENTS.md, not fork its content.
Avoid duplicated policy that diverges across agent products.
