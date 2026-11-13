---
id: YC-001
authority: current
owner: maintainer
applies_to: ["src/yougile_mcp/**", "catalog/**", "tests/**"]
superseded_by: null
---

# YC-001: YouGile API boundary

## Intent

YouGile HTTP operations have one shared implementation and contract surface,
used by all domain and smart MCP tools.

## Invariants

- **YC-001/INV1:** Each REST operation has one canonical client/adapter
  implementation, mapped by operationId, HTTP method and path.
- **YC-001/INV2:** Input validation, error translation, pagination and response
  envelopes are consistent across direct and compound callers.
- **YC-001/INV3:** No write is retried after an ambiguous result unless
  idempotency or deduplication prevents duplicate effects.
- **YC-001/INV4:** The API catalog distinguishes mapped operations, factual
  inventory, tested behavior and unsupported operations.
- **YC-001/INV5:** Shared per-company request limits are respected regardless
  of how many tools or agents call the API.

## Non-goals

This record does not dictate a specific HTTP library or prevent equivalent
transport implementations.

## Verification

API contract and integration tests prove schemas, pagination, errors and
retry behavior. Catalog checks report gaps without claiming live API proof.
