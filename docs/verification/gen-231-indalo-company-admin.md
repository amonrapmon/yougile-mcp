# GEN-231 · Indalo company admin (stage 26A)

Reuses Indalo AGPL admin pages from pinned commit
`ea88a0d5c5c055262cba9cf9741fd51828481ba5` as an authenticated
HTML interface for each company's **own YouGile administrators**.

## What works

- `/admin/login` verifies credentials against YouGile and requires admin
  membership in the chosen company. Multiple admin-company choice uses
  five-minute encrypted state with one-time consumption.
- Admin session is a random secure/HttpOnly/SameSite cookie, hashed key
  stored in Valkey with 8-hour TTL; state checked against active DB account
  on every request. Live YouGile `getMe.isAdmin` and company ID are
  verified on every admin operation.
- `/admin`: complete YouGile employee list with MCP connection and block
  status (including disconnected and departed people).
- `/admin/users/{id}`: Indalo-style card with **working** disconnect,
  block and unblock. CSRF, Origin and company-key isolation required.
- Preemptive bans are durable even for never-connected users: new
  `cloud_member_blocks` table, migration 002; checked during every
  sign-in and CloudTenantSessions.load, so OAuth cannot resurrect access.
  Disconnect/block deletes persisted credentials and refresh tokens
  transactionally, invalidating issued tokens, then asks YouGile to
  revoke the old key. Vendor revoke failures are audited for operator
  remediation. YouGile admins cannot be banned via company UI.
- `/admin/settings`: shows real company/account/access state and Full
  Access policy, not inert role/project/Workflow controls.

## Intentional separation

The upstream company's **roles/project allowlists/confirmations/Workflow**
require its original Tenancy/Policy engine. Ours uses 72-tool Full Access
bound to each person's own vendor account by explicit owner decision.
Those original settings will not be shown as if operational.

The **host owner** (cross-company server operator) is a different trust
boundary. Its administration must be implemented separately, with an
explicit owner allowlist and never using a company's admin status to
control other tenants.

## Tests and release

Tests use disposable PostgreSQL 16 + Redis 7, and schema-valid fake
YouGile API responses. They cover login/choice, admin-role revocation,
CSRF/Origin, unsafe user markup, preemptive bans, same-company controls,
user/session disconnect, company disable and cross-company isolation.

No new public listener or deployment permissions are added here.
Full remote-client verification and Traefik remain separate steps.
