---
id: YC-006
authority: draft
owner: maintainer
applies_to: ["src/yougile_mcp/**", "tests/**", "docs/references/**"]
superseded_by: null
---

# YC-006: MCP protocol and transport interoperability

## Intent

The remote MCP adapter provides a standards-based, authenticated interface
and negotiates compatible protocol versions without inventing a private
handshake or assuming every client speaks the latest revision.

## Invariants

- **YC-006/INV1:** The preferred protocol era is MCP 2026-07-28, with
  stateless, self-describing requests; this is separate from application
  state such as user identities and operation approvals.
- **YC-006/INV2:** The server uses a maintained SDK with explicit support for
  the chosen protocol version. It does not invent session-based control
  messages for modern clients, nor assume old clients support the modern era.
- **YC-006/INV3:** In the 2026 era, version, method and named-tool routing
  headers are validated consistently with the request body. Do not bypass
  SDK-provided protocol validation.
- **YC-006/INV4:** Client capabilities and optional extensions are detected
  before use. Modern capability discovery uses server/discover; legacy
  clients follow their supported handshake semantics.
- **YC-006/INV5:** Structured outputs respect the negotiated JSON Schema
  dialect, bounded size, result/error semantics and stable tool naming.
- **YC-006/INV6:** A proxy or middleware cannot strip authorization or
  routing metadata; trusted origin handling, redirects and forwarded
  headers have dedicated negative tests.
- **YC-006/INV7:** If future work uses MCP Tasks, MCP Apps or MRTR, it
  must negotiate extension support and preserve fallbacks rather than
  assuming every client supports these optional features.

## Non-goals

This record does not require MCP extensions, a database-backed MCP
transport session, SSE, or an extra home-grown wire protocol. Client
compatibility decisions require verified SDK and client evidence.

## Verification

MCP conformance and negative transport tests with clients supporting both
modern 2026-07-28 and selected legacy revisions, schema validation,
capability-negotiation tests, auth header tests and gateway routing checks.

## Sources

- https://modelcontextprotocol.io/specification/2026-07-28
- https://blog.modelcontextprotocol.io/posts/2026-07-28/
- https://py.sdk.modelcontextprotocol.io/whats-new/
