---
id: YC-004
authority: current
owner: maintainer
applies_to: ["Dockerfile", "compose.yaml", ".env.example", ".github/workflows/**", "src/yougile_mcp/**"]
superseded_by: null
---

# YC-004: Self-hosted deployment contract

## Intent

YouGile MCP is deployable as an independently hosted server without relying
on an agent user's desktop/browser session.

## Invariants

- **YC-004/INV1:** Remote MCP uses authenticated Streamable HTTP behind HTTPS,
  with independent actor identities.
- **YC-004/INV2:** No unauthenticated listener or public container port is
  exposed by default.
- **YC-004/INV3:** Runtime secrets come from protected configuration, not
  images, repositories or logs.
- **YC-004/INV4:** Container processes use minimum required permissions;
  failure and restart behavior are observable and documented.
- **YC-004/INV5:** CI validates source, tests, packaging, security-sensitive
  policy checks and image build before a release is promoted.

## Non-goals

The contract does not mandate a particular reverse proxy or data store,
although the initial target environment uses Traefik.

## Verification

Docker/Compose smoke tests, identity-aware remote MCP integration, negative
transport configuration tests and deployment readiness checks.
