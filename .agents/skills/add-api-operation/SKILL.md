---
name: add-api-operation
description: Add or update a YouGile REST v2 operation without bypassing API contracts.
---

# Add a YouGile API operation

Use when a YouGile operationId, endpoint, DTO or API error changes.

1. Read AGENTS.md and the nearest nested AGENTS.md.
2. Route affected paths: python scripts/agent_contracts.py for catalog/openapi-operations.json src/yougile_mcp/config.py
3. Read .agents/rules/api.md, .agents/rules/security.md and the current
   API/authorization records.
4. Verify the operationId, HTTP method, URL, headers, schema and error cases
   against public OpenAPI and actual isolated test-company behavior.
5. Implement in shared API/client layer; register direct MCP tool only via
   domain adapter, with scopes and audit classification.
6. Test validation errors, pagination, 204, rate limits and retry safety.
7. Update coverage map and docs, then run invariant and unit checks.
