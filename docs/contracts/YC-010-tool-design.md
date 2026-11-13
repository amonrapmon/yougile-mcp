---
id: YC-010
authority: draft
owner: maintainer
applies_to: ["src/yougile_mcp/**", "catalog/**", "tests/**", "docs/references/**"]
superseded_by: null
---

# YC-010: MCP tool contracts, compatibility and ergonomics

## Intent

The MCP tool catalog exposes all verified YouGile capabilities with
predictable stable schemas, safe composition and limited token usage.

## Invariants

- **YC-010/INV1:** Each tool has a documented purpose, required inputs,
  validated JSON Schema, result schema, error categories, permission scopes,
  side effects, max payload and pagination behavior.
- **YC-010/INV2:** Read operations, writes and destructive actions are
  explicitly classified; high-risk actions are not silently labeled read
  or hidden inside a convenience tool.
- **YC-010/INV3:** Smart tools reuse canonical API operations with the same
  scopes, per-company limits, audit and retry rules. They do not expose
  shortcut HTTP clients or bypass approvals.
- **YC-010/INV4:** Public tool renames, schema changes and default changes
  have a compatibility/deprecation plan; the historical 75-tool inventory
  remains a functionality target, not implemented-feature evidence.
- **YC-010/INV5:** Responses are structured, bounded, sortable/stable and
  use explicit fields/compactness controls without silently dropping
  information necessary to act safely.
- **YC-010/INV6:** Tool errors clearly distinguish validation, permission,
  not-found, rate-limit, vendor failure and uncertain-write outcomes.
  A genuine tool failure is not masked as a success string.
- **YC-010/INV7:** Optional MCP extensions are opt-in and feature-detected;
  unsupported clients receive a safe basic-tool fallback.

## Non-goals

This record does not require one MCP tool per REST method, force exactly 75
runtime registrations, or require optional UI extensions.

## Verification

Tool discovery/schema tests, denied-scope cases, golden compatibility
fixtures, output-budget tests and a real multi-step workflow on safe test data.

## Sources

- https://modelcontextprotocol.io/specification/2026-07-28
- https://ru.yougile.com/api-v2
