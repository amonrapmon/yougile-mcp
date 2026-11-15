# GEN-231 Cloud persistence (PR #23)

Design adapted from Indalo's AGPL-3.0 server, commit
ea88a0d5c5c055262cba9cf9741fd51828481ba5, © Indalo.
Cloud is an optional extra; local stdio users need no Postgres/Valkey.

## Durable storage

- PostgreSQL migration: advisory transaction lock, schema version, no billing/trial tables.
- User identity unique by (company_id, yougile_user_id). Each stores an independently encrypted YouGile API key. Both company and user are disableable.
- CloudCipher uses MultiFernet encryption with key rotation. Neither API keys nor user passwords enter logs or JSON responses.
- OAuth clients and hashed refresh tokens live in PostgreSQL. Refresh-token consumption is one-shot via DELETE RETURNING.
- Valkey holds OAuth transient flow/code state, revoked JWT IDs, login failure counters and atomic company request budget.

## Next-stage lifecycle

CloudTenantSessions resolves its per-request account through PostgresCloudStore.load().
After successful CloudYouGileSignIn.provision(), the OAuth sign-in handler must
call save_account() and revoke the old API key after committing; it must revoke
a newly issued key if persistence fails. If old-key revocation fails, a durable
retry path is required. The OAuth HTTP handler and credential orchestration
have not yet been implemented.

Back up the DB and Fernet encryption keys together. A lost Fernet key makes
encrypted vendor keys unrecoverable. Never expose Valkey or PostgreSQL publicly.
Use uv sync --locked --extra cloud for the hosted service.

This PR does NOT expose remote HTTP/OAuth or the admin UI. Real vendor
multi-company authentication and full OAuth E2E remain separate release gates.
