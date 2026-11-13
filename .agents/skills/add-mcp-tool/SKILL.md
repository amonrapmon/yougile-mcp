---
name: add-mcp-tool
description: Implement or change a direct or smart MCP tool with permission and compatibility tests.
---

# Add or change an MCP tool

Use for any new tool name, schema, tool description, smart/compound operation
or tool removal.

1. Route files and read current tool contract(s).
2. Check whether an existing API operation/tool already expresses this
   behavior; reuse instead of creating redundant tools.
3. Specify input/output, pagination and size limits, failure envelope,
   required scopes and whether the operation may have side effects.
4. Ensure smart tools use one shared API client and policy per action.
5. Plan timeout/retry/idempotency behavior and protected-action approval.
6. Add contract tests for granted and denied principals and partial failure.
7. Update catalog and compatibility notes; prove no loss of existing
   functional scenarios.
