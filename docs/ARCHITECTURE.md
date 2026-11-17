# Architecture

This document describes the implementation in the `main` codebase as reviewed on 2026-11-15. It separates **implemented components** from **release gates and planned features**. [README](../README.md) is the product overview; [client setup](clients/README.md) contains connection examples.

## System overview

~~~text
AI clients / local coding agents                 AI clients / hosted connectors
          |                                                   |
        stdio                                     HTTPS Streamable HTTP + OAuth
          |                                                   |
  mcp/stdio.py + runtime.py                        cloud/server.py + web.py
          |                                      OAuth provider and tenant sessions
          |                                                   |
          +--------------------+------------------------------+
                               |
                      MCP Tool Registry
             factory.py + policy-manifest.json
                               |
                       ToolDispatcher
             per-actor / company verification
              project ownership / approval gates
                               |
                      Unified API Client
                   api/client.py + api/spec.py
                               |
                        YouGile REST v2
~~~

For the hosted mode, PostgreSQL stores encrypted cloud account state, refresh grants, member blocks and administration records; Valkey stores ephemeral OAuth/session and revocation state. The private admin UI is hosted within the same HTTP application. Neither database is used as a substitute for vendor permissions.

## Implemented layers

### Official API contract and client

- `src/yougile_mcp/api/` loads a pinned official YouGile OpenAPI 3.0.0 document for REST API v2 and a hash-bound compatibility overlay. The vendor snapshot is not mutated to disguise live differences.
- One asynchronous `YouGileClient` implements the operation contract. Request/response validation, pagination, bounded retries and normalized errors live here.
- API client rate limiting is process-local, at most 50 calls per minute per company. **Multiple production replicas require a coordinated limiter**.
- Requests with uncertain write outcomes are not blindly retried.

### MCP registry and execution

- `mcp/factory.py` generates **72 direct MCP tool descriptors** from the matching API operation definitions and reviewed policy manifest. Names use the `yg_v2_` prefix.
- `mcp/runtime.py` and `mcp/cloud.py` expose tools using the official MCP Python SDK 2.3.0. Listing a tool is separate from authorizing its invocation.
- `mcp/dispatch.py` validates arguments and results, checks the actor's company and operation scopes, verifies company/resource ownership, protects credential fields, and sanitizes errors. It enforces file and output size budgets.
- **Important:** operations marked `requires_approval` and certain destructive updates return `approval_required` unless a trusted approval provider is injected. Hosted and stdio launchers do not currently provide one. A narrowly reviewed exception permits `ProjectController_create` to run without server approval only for a nonblank `title` and optional `idempotencyKey`, with the usual company/scope checks intact. Supplying `users` or `departments` (even as empty objects) still requires approval. See [the draft policy decision](contracts/YC-011-project-create-approval.md). Credential operations requiring server-side secret injection also fail closed without a resolver. Therefore **72 registered descriptors does not mean 72 operations are executable under the default hosts**.
- A separate, agent-friendly smart/compound tool layer remains a planned capability. Do not imply the direct API parity layer already provides natural-language task resolution or bulk workflows.

### Local stdio host

- `yougile-mcp serve` launches stdio only. The host requires `MCP_TRANSPORT=stdio`, `YOUGILE_API_KEY`, `YOUGILE_COMPANY_ID` and an absolute protected `MCP_STDIO_IDENTITY_FILE`.
- Each local child process uses exactly one explicitly provisioned principal. On POSIX, the identity file must be owned by the process user with no group/other access.
- No network listener is opened in stdio mode. [Local installation guide](clients/local-stdio.md).

### Hosted OAuth / Streamable HTTP

- `yougile-mcp cloud-serve` requires `MCP_TRANSPORT=http`, `MCP_HOST=127.0.0.1` (or another supported loopback spelling), an HTTPS `MCP_PUBLIC_URL`, PostgreSQL, Valkey, JWT signing and encryption secrets. It rejects process-global YouGile API keys/company IDs.
- `cloud/server.py` binds the HTTP listener to **loopback only**, not public interfaces. OAuth 2.1, PKCE, client registration, token verification/rotation and revocation are handled by `cloud/oauth.py` and the official MCP SDK.
- The endpoint is `<MCP_PUBLIC_URL>/mcp`. User sign-in creates a distinct company-bound YouGile account credential; a trusted account repository, not MCP arguments, supplies the company and key per invocation.
- `cloud/redirects.py` explicitly restricts OAuth callback origins to default trusted Claude origins, loopback native-client callbacks, and additional operator-approved entries from `CLOUD_OAUTH_REDIRECT_ORIGINS`.
- OAuth currently provides `yougile.full`, limited by the authenticated person's YouGile access and selected company. This **is not** configurable project-level OAuth RBAC.

### Administration

- Company admin endpoints include `/admin/login`, `/admin`, `/admin/users/{id}` and `/admin/settings`. They use vendor administrator verification and server-side session/access checks; connected users can be disconnected or blocked.
- `/host` is a **separate hosting-operator control plane**, enabled only by explicit `CLOUD_HOST_ADMIN_SUBJECTS` pairs. YouGile company administration does not implicitly grant hosting-operator privileges.
- Re-enabling a disabled company does not resurrect previously invalidated access tokens or admin sessions.
- Admin views adapt portions of the AGPL-licensed Indalo implementation. See [PROVENANCE](PROVENANCE.md) and [host/admin verification](verification/gen-231-indalo-host-control.md).

## Deployment boundary

The checked-in `Dockerfile` and `compose.yaml` are **offline configuration-check scaffolds**. The container defaults to `yougile-mcp doctor` and publishes no HTTP ports. The application code for a private OAuth HTTP shell exists, but the repository does **not** provide a completed, publicly approved HTTPS/Traefik deployment. Do not bind it directly to the internet or treat the scaffold as production-ready.

Public release requires at least: trusted TLS termination and request-origin handling; end-to-end tests with real MCP clients and a disposable YouGile company; production readiness/security review; distributed rate-limit decisions; and the separate licensing review for distributing the vendor OpenAPI snapshot. See [PROVENANCE](PROVENANCE.md), [live verification](verification/gen-229-live-e2e.md) and [ROADMAP](ROADMAP.md).

## Architecture invariants

1. Every YouGile REST operation has one canonical API client implementation.
2. Authentication and trusted account resolution precede any tool invocation.
3. Discovery/visibility is not authorization; the dispatcher rechecks execution permissions.
4. MCP tool input cannot select another company's key or change the authenticated actor.
5. Missing approval, credentials, account state or storage fails closed.
6. Vendor-controlled task, chat and file content must never become trusted instructions.
7. Secrets must remain server-side, never in tool responses, agent prompts or committed config.
8. Public transport must not bypass the same API client and company/resource checks.
9. Changes to public tool contracts and security boundaries follow [AGENTS.md](../AGENTS.md) and applicable CURRENT records in `docs/contracts/`.
