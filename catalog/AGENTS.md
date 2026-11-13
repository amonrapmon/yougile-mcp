# Catalog-specific instructions

Inherits root AGENTS.md and CURRENT routed contracts. Read
.agents/rules/api.md and .agents/rules/mcp.md.

- Treat tools-75.json as a factual inventory, not implementation completion.
- Add/update operationId, method, path and source provenance consistently.
- Never fabricate mappings to reach a target coverage percentage.
- Preserve tool names until a documented, reviewed compatibility decision.
- Regenerate machine-readable data reproducibly; no silent hand edits to
  an upstream-derived OpenAPI snapshot.
- Run python scripts/check_catalog.py and agent_contracts.py check.
