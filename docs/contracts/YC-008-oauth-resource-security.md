---
id: YC-008
authority: draft
owner: maintainer
applies_to: ["src/yougile_mcp/**", "tests/**", "compose.yaml", ".env.example", "docs/references/**"]
superseded_by: null
---

# YC-008: Remote MCP OAuth and authorization boundary

## Intent

A remote MCP invocation is authorized for one identified agent, company,
allowed project and operation, independent of how the client discovers tools.

## Invariants

- **YC-008/INV1:** MCP resource access uses signed/verified bearer tokens
  or equivalent policy with correct issuer, intended audience, expiry,
  revocation and scoped authorization. YouGile keys remain server-side.
- **YC-008/INV2:** OAuth protected-resource discovery and authorization
  server metadata are implemented per the selected protocol version,
  without confusing the resource server with the authorization server.
- **YC-008/INV3:** Prefer the modern Client ID Metadata Document flow
  where clients and authorization server support it; DCR compatibility
  is explicit, not the undocumented sole design.
- **YC-008/INV4:** Scope evaluation and company/project isolation run on
  every direct and nested smart-tool action, regardless of advertised
  tools or client-selected company identifiers.
- **YC-008/INV5:** Elevated scopes and destructive operations use explicit
  authorization. Approvals are bound to payload, actor and expiry and
  prevent replay and substitution.
- **YC-008/INV6:** Public transport enforces HTTPS, trusted origin,
  safe redirects, no bearer token forwarding to unrelated origins, and
  protection of refresh tokens/API keys at rest and in logging.
- **YC-008/INV7:** No untrusted external description, task body or chat
  content becomes an instruction to change policy or skip a guard.

## Non-goals

This record does not commit to a specific identity provider, DB/Redis
backend, or the copied implementation from another project.

## Verification

OAuth and token-isolation tests, cross-tenant denial, bad issuer/audience,
expiry/revocation, insufficient_scope, redirected tokens, forged approval,
and auth-required HTTP smoke against a real client.

## Sources

- https://modelcontextprotocol.io/specification/2026-07-28
- https://apps.extensions.modelcontextprotocol.io/api/documents/authorization.html
