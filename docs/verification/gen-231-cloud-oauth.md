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

## OAuth redirect regression: DE reconnect (2026-11-16, fix branch)

On DE, a company selection produced these server stages:
`authorization_created`, `signin_get_valid`, `company_choice_rendered`,
`company_post_received`, `company_post_claimed_credentials`,
`vendor_account_provisioned`, `cloud_account_saved`,
`oauth_redirect_issued`.
The browser did not visibly advance and no refresh token was issued.
This does **not** prove that YouGile key revocation was the sole failure.
The previous implementation issued its OAuth redirect **only after**
calling synchronous old-key revocation, following `oauth_redirect_issued`.

This fix:
- atomically enqueues the *old encrypted key* with account replacement;
- returns the OAuth 302 without calling the YouGile delete endpoint;
- uses a PostgreSQL-backed worker with lease, 8-second timeout, bounded
  exponential retry, and 404-as-success semantics for uncertain deletes;
- emits safe `old_key_revoke_enqueued` / `redirect_response_ready` stages,
  plus background `old_key_revoke_started`, `old_key_revoke_finished`
  and `retry_scheduled` (numeric job IDs only, no key material);
- preserves the pending work across worker/container restarts.

The work queue is introduced in `004_vendor_key_revocations.sql`, applied
by the existing startup migration mechanism. Before deployment, take a
PostgreSQL backup and retain `CLOUD_ENCRYPTION_KEYS` for queued ciphertext.
Rollback to a pre-migration application can leave pending jobs unprocessed;
do not drop the outbox until all queued revocations are reconciled. This fix
does not by itself certify a successful live ChatGPT OAuth callback or a
completed token exchange, which require a separate on-DE acceptance test.

## Browser-blocked OAuth callback: CSP `form-action` (2026-11-16)

On DE the browser network trace confirmed `POST /signin/company` returned
HTTP 302 and `Location: https://chatgpt.com/connector/oauth/...`. The server
also logged `redirect_response_ready`, but the browser remained on the
company selection page. The shared HTML Content Security Policy included
`form-action 'self'`. Browsers enforce this directive on redirects following
a form submission, including cross-origin OAuth callback navigation.

The login and company-selection forms now use a dedicated OAuth page CSP
without `form-action`, allowing client callbacks and multi-hop client
redirects. **All other CSP restrictions remain** (`default-src 'none'`,
`frame-ancestors 'none'`, `base-uri 'none'`, no inline scripts). Normal
pages and administrative forms retain `form-action 'self'`. OAuth POST
handlers still enforce exact Host/Origin, HMAC CSRF, verified callbacks and
one-time flows.

HTTP-level regressions assert the policy distinction on both OAuth forms
and the landing page. Browser-side confirmation (Console free of CSP
form-action violations, callback loaded, server `/token` exchange and
positive refresh-token persistence) must be checked on the real DE browser.
No private OAuth URL, token, raw flow ID or CSRF value is stored in docs.
