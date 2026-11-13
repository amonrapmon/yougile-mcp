# External standards reference index

Source of truth is external documentation, **not** a copied or rewritten
protocol specification. standards.json pins the reference versions currently
used for design and flags unresolved compatibility choices.

Read the applicable CURRENT architectural contract first. A DRAFT contract
is a proposed technical decision and **cannot** authorize a new behavior.

Axes that must never be conflated:

- **MCP**: protocol revision 2026-07-28 (wire-level requests, auth and tools).
- **OpenAPI**: format standard OAS 3.2.1, published September 10, 2026.
- **YouGile**: public vendor REST API **v2**, independent of OAS syntax.
  The official pinned contract uses \`openapi: 3.0.0\`.
- **Python SDK**: a maintained v2 release that supports the new and legacy
  protocol eras; its version is not the MCP specification revision.

Do not "upgrade" vendor OpenAPI 3.0 data to OAS 3.2 by search-and-replace.
Do not claim a pinned operation listing proves vendor endpoint availability,
successful DTO decoding or complete production behavior.

Standards should be periodically reverified and their snapshot provenance
updated by a focused review PR. A version change is a contract review, not
routine housekeeping.

## YouGile REST API v2 source

The official OpenAPI document is published at
<https://ru.yougile.com/api-json> and is pinned in
\`src/yougile_mcp/api/openapi-v2.json\`. It identifies YouGile API v2.0 and
OpenAPI 3.0.0; the latter is a document format version, not an API version.
The SHA-256, retrieval date, author attribution and license status are in
\`src/yougile_mcp/api/openapi-source.json\`. The source document does not
declare a license. The official contract currently has 72 operations; the
coverage matrix in \`catalog/openapi-operations.json\` is generated from this
snapshot and distinguishes discovered operations from mock-tested ones.

Do not generate DTOs from the operation matrix alone; use the pinned source
schema and review any drift before updating it.

The \`catalog/openapi-operations.json\` file is only an operation inventory,
not the full vendor OpenAPI schema. Do not generate DTOs from it.

## UTCP: explicitly deferred extension

Universal Tool Calling Protocol (UTCP) v1.1 describes direct native API calls
using a discoverable tool manual. It is a different integration model from
MCP, not a new version of MCP.

Decision for this project: **design for a future UTCP adapter, do not
implement one in the MVP**. Keep tool schemas, typed operations, authorization
and audits in a protocol-independent core. Future clients must call only
secured, explicitly exposed endpoints of *our* service with their own
principals, never a privileged YouGile key or an unprotected direct API.

Source: https://www.utcp.io/docs/
