# GEN-231 stage 26B · Owner-level multi-company administration

This PR is stacked on company-admin PR #26. It introduces a separate
host-operator authorization plane, **not** a superuser role inferred
from YouGile company membership.

## Setup

Set `CLOUD_HOST_ADMIN_SUBJECTS` only on the private self-hosted server
to a comma-separated list of exact pairs:

```env
CLOUD_HOST_ADMIN_SUBJECTS=company-id-from-yougile:vendor-user-id
```

The vendor user must log into `/admin/login` for exactly that company
and have current `UserController_getMe.isAdmin=true`; the server verifies
the stored account and vendor company on **every** request.

No configured host subjects -> `/host` routes do not exist (404).
A regular company admin can only use `/admin` for **their own** company.

## Existing Indalo-derived pages

- `/host`: lists cloud companies, status, connected/block counts, and
  buttons to disable or re-enable *other* companies. Current owner
  company cannot be disabled from this page.
- `/host/companies/{id}`: connected cloud users and preemptive blocks;
  server-owner actions: block, unblock, disconnect. Server owner does
  not load the target company's full YouGile employee list or see keys.
- Company admins retain `/admin` screens and cannot call any host
  actions unless the explicit operator allowlist matches.
- All modifying routes use the same Indalo-derived CSRF/Origin/Host
  checks and vendor-verified session as the company admin. No anonymous
  operations, project RBAC or different UI framework.

## Revocation semantics

Migration `003_host_epoch.sql` adds an access epoch per company.
`set_company_enabled()` increments it on state changes and deletes
active refresh grants on disable. New access JWTs and admin sessions
contain the current epoch, checked against PostgreSQL on every request.
Re-enabling a company does **not** reactivate stale OAuth JWTs/cookies.

Blocking a user deletes their cloud account and OAuth refresh grants,
preventing reuse of previously issued user tokens even after unblock.
Failed external YouGile key revocations are recorded as audit events
without plaintext keys, pending durable retry design.

## Testing / release boundary

Real PostgreSQL 16 + Redis 7 and fake vendor responses verify:
- strict host allowlist and vendor admin revalidation;
- company isolation, CSRF, unknown IDs, self-lockout protection;
- actual cross-company member blocking and server key revocation;
- JWT and admin cookie invalidation after disable/re-enable;
- existing 72-tool OAuth and company-admin regressions.

No public deploy, Traefik changes or live vendor E2E in this PR.
