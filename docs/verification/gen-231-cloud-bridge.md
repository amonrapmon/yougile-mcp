# GEN-231: multi-company cloud bridge (stage 1)

## Upstream and provenance

Migration target: [indalo-tech/yougile-mcp-cloud](https://github.com/indalo-tech/yougile-mcp-cloud)
at commit `ea88a0d5c5c055262cba9cf9741fd51828481ba5` (2026-10-29),
AGPL-3.0-only, © Indalo. The upstream includes already implemented OAuth 2.1,
PKCE, client registration, HTML sign-in, company choice, Postgres/Valkey
storage, encrypted per-user keys, admin screens, and a test harness.

This PR is a new compatibility adapter in our AGPL project; it does not
yet copy upstream source modules. Refer to docs/PROVENANCE.md when those
modules are imported; preserve source copyright notices and license.

## Why an adapter is required

Indalo's `yougile_cloud.app` calls its own
`yougile_mcp.server.build_server` (FastMCP) and
`yougile_cloud.tenancy` builds its own Runtime/Policy/Directory.
Our core instead has the official Python MCP SDK v2 `Server` with 72 dynamic
descriptors and `ToolDispatcher`. Copying `oauth.py` without remapping
that runtime would silently execute someone else's tools.

This stage provides `CloudTenantSessions` and `make_cloud_mcp_server`.
A future hosted adapter passes only an **already verified** user ID from a
signed OAuth access token; the DB resolves that ID to the user's own encrypted
YouGile API key and company ID. The bridge is deliberately unable to read a
global API key or to accept a company ID from a tool request. Each call
creates its own company-bound client, verifier and dispatcher. Account bans
and credential rotation apply to the next request. All 72 registry tools
are visible in the full-access profile. Project-specific operations still
resolve the resource via the caller's own company-scoped YouGile key.

## Next stage: port the real cloud shell

1. Adapt upstream OAuth/PKCE/refresh/DCR and tested sign-in/choose-company
   pages, keeping their CSRF, redirect allowlist, rate limits and secret rules.
2. Adapt its persistence and key encryption, then connect the verified
   OAuth user ID to `CloudTenantSessions`.
3. Replace the upstream `FastMCP` core registration with the official Python MCP
   SDK v2 Streamable HTTP ASGI adapter. Do not expose any endpoint until
   anonymous, revoked and cross-company negative HTTP tests pass.
4. Disable trial/payment gating by default. Preserve administrative
   company/user blocks; exclude the unrelated Telegram tickets bot.
5. Add container/Traefik deployment with no unauthenticated public routes,
   shared company-wide limiter and real client E2E.

No HTTP listener, new auth provider, DB, or administrative UI is introduced
by this PR. This is not the completed Indalo migration and not a remote MVP.
The 72/72 tests here prove registry visibility and selected cross-company
calls, **not** 72 live vendor operations.
