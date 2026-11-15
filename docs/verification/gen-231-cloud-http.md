# GEN-231: OAuth-protected Streamable HTTP shell (PR #25)

This stage composes the existing official MCP SDK v2 Server, SDK OAuth
endpoints + Bearer middleware, DB-backed OAuth and the Indalo sign-in/company
pages into one **private-loopback** HTTP application.

## Endpoint contract

- `GET /` for setup URL; `GET /healthz` for liveness (no secrets)
- `GET /signin`, `POST /signin`, `POST /signin/company` for
  server-rendered YouGile login, short-lived choice and CSRF
- SDK `/.well-known/oauth-authorization-server`,
  `/.well-known/oauth-protected-resource/mcp`, `/authorize`,
  `/register`, `/token` and `/revoke`
- SDK Streamable HTTP `/mcp` with required `yougile.full` Bearer scope,
  verified issuer and audience, no anonymous fallback.
- MCP SDK `CloudTenantSessions` maps the verified OAuth subject to the
  separate company/YouGile API key in encrypted PostgreSQL.

## Lifecycle and boundaries

- `yougile-mcp cloud-serve` requires
  `MCP_TRANSPORT=http`, a loopback `MCP_HOST` and public HTTPS origin
  `MCP_PUBLIC_URL`. It never binds a public interface. HTTPS termination,
  reverse proxy auth headers/Host preservation, CSRF protection and separate
  public deployment validation are mandatory.
- Required: `CLOUD_DATABASE_URL`, `CLOUD_VALKEY_URL`,
  `CLOUD_JWT_SECRET` (at least 32 characters of entropy),
  `CLOUD_ENCRYPTION_KEYS` (comma-separated Fernet keys).
  Optional: `CLOUD_OAUTH_REDIRECT_ORIGINS` (explicit allowlist).
- PostgreSQL and Valkey must remain on private networks.
- User password is not stored persistently. For multi-company selection it
  lives at most 5 minutes encrypted in Valkey and is consumed once with
  atomic `GETDEL`. HTTP bodies, form origins/CSRF and login attempts are limited.
- After successful login the backend stores each person's own encrypted
  YouGile key, issues the OAuth authorization code and attempts to revoke
  the previous key. If vendor revocation fails, a non-secret audit event is
  saved; automatic durable retries have not yet been implemented.
- OAuth access token revocation, disabled-account checks, rotated refresh
  and cross-company separation are enforced by the existing provider/store.
- No Keycloak, subscriptions, billing or extra IAM-role editor.

## Remaining release gates

The merged `main` already has #20–#24. This PR is an HTTP implementation,
but it is **not** an authorization to publish to the internet or a public
production release. PR #26 must add deployment/Traefik/HTTPS hardening,
source-available AGPL notice for network use, administrative disable UI,
end-to-end real MCP clients, and live YouGile compatibility checks.
The test suite uses disposable PostgreSQL/Redis and a fake vendor API.

Upstream credit: Indalo `yougile-mcp-cloud` @
`ea88a0d5c5c055262cba9cf9741fd51828481ba5`
(© Indalo, AGPL-3.0-only). The forms, company choice and
security-header ideas were adapted into the SDK-native HTTP shell.
