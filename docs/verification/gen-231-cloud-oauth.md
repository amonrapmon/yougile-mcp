# GEN-231 OAuth provider (PR #24)

Uses official Python MCP SDK v2 OAuthAuthorizationServerProvider-compatible
methods and data models (no custom HTTP OAuth protocol). Adapted after
Indalo's oauth.py at commit ea88a0d5c5c055262cba9cf9741fd51828481ba5,
© Indalo, AGPL-3.0-only.

Supported provider actions:
- registered client persistence and a strict allowed-redirect list;
- OAuth authorization request → temporary Valkey flow;
- login flow finalization by trusted user ID → one-shot authorization code;
- SDK-driven PKCE S256 enforcement and code exchange;
- signed access JWT restricted by issuer, audience, expiry and token type;
- hashed durable refresh tokens rotated atomically; replays refused;
- access JTI revocation and immediate denial of disabled company/user;
- strict no anonymous fallback. API keys are not embedded in any OAuth token.

Stage #24 still does not mount HTTP OAuth routes or credential forms. The next
stage must use SDK create_auth_routes and bearer middleware, connect safe
server-rendered login+company pages and CSRF/attempt rate limits, and mount
StreamableHTTPSessionManager under a verified principal, never public before
negative cross-tenant and anonymous tests. No Keycloak, own admin UI or billing.
