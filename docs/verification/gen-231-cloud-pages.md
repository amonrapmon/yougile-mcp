# GEN-231 · Indalo login-page port (stage 2)

Two upstream **AGPL-3.0** modules are copied from
https://github.com/indalo-tech/yougile-mcp-cloud at immutable
`ea88a0d5c5c055262cba9cf9741fd51828481ba5` (2026-10-29):

- `src/yougile_mcp/cloud/pages.py`: login form, company-choice form,
  informational/error pages, CSS; original behavior preserved and source links
  updated to credit both our repository and Indalo.
- `src/yougile_mcp/cloud/redirects.py`: vetted OAuth redirect origins and
  native-client loopback/callback rules, unchanged logic.

The modules are importable, packaged and covered by escaping and redirect
allowlist tests. **They are not HTTP routes yet.** No login form is reachable
without an approved OAuth provider and proper POST/CSRF handler.

Next: adapt upstream OAuth provider, company credential issuance and encrypted
PostgreSQL storage, connect the verified user identity to the CloudTenantSessions
from PR #20. The commercial paywall and unrelated Telegram ticket bot are out
of scope. No public MCP route until negative cross-tenant/auth tests pass.
