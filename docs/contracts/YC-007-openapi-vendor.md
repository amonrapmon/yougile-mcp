---
id: YC-007
authority: draft
owner: maintainer
applies_to: ["src/yougile_mcp/**", "catalog/**", "tests/**", "docs/references/**"]
superseded_by: null
---

# YC-007: OpenAPI-first YouGile API integration

## Intent

The YouGile REST v2 surface is derived from verifiable vendor operations,
not inferred from MCP tool names or an agent's memory of endpoint shapes.

## Invariants

- **YC-007/INV1:** Vendor API version, OpenAPI document version and
  MCP protocol version are separate independent axes. YouGile REST v2
  cannot be relabeled v3 because the vendor document says openapi: 3.0.0
  or the global OpenAPI standard is now 3.2.1.
- **YC-007/INV2:** Each operation owns one canonical method, path,
  operationId, request/response schema, required credentials, pagination
  contract and documented error response behavior.
- **YC-007/INV3:** Inputs are validated before the HTTP call; successful
  responses and error bodies are validated/decoded into shared DTO types.
  Optional/required distinctions cannot be silently guessed.
- **YC-007/INV4:** HTTP 204 and missing bodies, cursor/list pagination,
  nested task fields, permission errors, rate limits, and uploads have
  explicit tests and bounded output behavior.
- **YC-007/INV5:** The official vendor API docs are checked for freshness.
  Snapshot hash, source, retrieval date and any spec drift are recorded
  when a pinned snapshot changes.
- **YC-007/INV6:** API coverage compares every operation to an actual
  client implementation or a reviewed exclusion. An inventory of 75 tool
  names cannot count as passing coverage.
- **YC-007/INV7:** Tool adapters call the same typed API client, and direct
  REST access from the MCP tool layer is disallowed.

## Non-goals

This record does not mandate regenerating all runtime models from OpenAPI,
nor change the vendor's schema dialect. It does not assume public docs alone
prove real API behavior.

## Verification

Contract tests from a pinned spec, snapshot-diff review, DTO and pagination
edge-case tests, and read/write checks against a disposable YouGile company.

## Sources

- https://ru.yougile.com/api-v2
- https://spec.openapis.org/oas/latest.html
