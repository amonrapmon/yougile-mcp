# Architecture contract

Current code is an offline foundation, not a YouGile-integrated MCP server.

## Planned layers

- config: validated environment, secret providers and typed configuration.
- api/client: shared async YouGile HTTP client, errors, retry, pagination,
  rate limit, caching and idempotency.
- api/catalog: complete, versioned mapping from the official OpenAPI spec.
- mcp/domain: full low-level API operations, preserving the 75-tool functional
  inventory and adding missing API features.
- mcp/smart: tasks by number and name, resolved users/boards, Workflow moves,
  context and history, comments, files, bulk and compound operations.
- security: OAuth 2.1, per-agent scopes, project allowlists, approvals, audit.
- transport: authenticated Streamable HTTP exposed via TLS and Traefik.
- deployment: non-root Docker, health/readiness, migrations, secrets and metrics.

## Structural invariants

1. Each REST operation has exactly one API implementation.
2. Domain and smart tools use identical permissions, policy and audit enforcement.
3. Unknown operationId from OpenAPI fails contract CI until addressed.
4. Tool discovery may be filtered per agent, execution is always rechecked.
5. Comments/task text never become trusted system instructions.
6. YouGile credentials remain server-side; every actor has an identity.
7. No unauthenticated remote listener or local filesystem exposure.
8. Company rate limits are respected across sessions and replicas.
9. Retry only safe/idempotent operations; every write is traced.
10. Production releases require tests using a disposable YouGile company.

## Dependencies and lockfile

Python 3.11+ is the baseline. The initial package has no production
dependencies, so no lockfile is checked in. When FastMCP / HTTP client
dependencies are first added, generate and commit uv.lock and change CI and
Docker to use locked installation. Do not hand-edit locks.
