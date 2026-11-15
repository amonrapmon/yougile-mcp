# GEN-231 · Remote principal authorization foundation

This PR introduces a **transport-independent** authorization gate for an already
verified OAuth bearer identity. It does not implement a JWT signature verifier,
OAuth issuer, HTTP listener or token endpoint.

## Trust chain

1. External IdP signs an access token specifically for the MCP resource.
2. A future SDK `TokenVerifier` MUST verify token authenticity/signature or
   introspection, issuer and audience before constructing `VerifiedBearer`.
   Do not construct it directly from decoded, unsigned JWT claims.
3. `RemotePrincipalGate.resolve()` checks issuer, audience, nbf/expiry,
   presence of token ID, revocation and an authoritative server-side agent
   grant on **every request**.
4. Scope is the intersection of verified token scopes, stored grant scopes
   and registered known scopes. Company ID and allowed projects come from
   server-managed grant data, never from MCP arguments or token claims.
5. The resulting `InvocationPrincipal` is handled by the same Registry,
   CompanyVerifier, ProjectOwnershipResolver and Dispatcher as local stdio.

Unknown, revoked, expired, cross-company, cross-client or disabled identities
are refused; storage outages also fail closed. No token bytes are logged.

## Integration gates before remote exposure

- Select/approve external OAuth AS (OIDC/OAuth metadata, PKCE S256, audience),
  Client ID Metadata Document or registered client policy, and refresh/revoke.
- Implement and verify the SDK `TokenVerifier` adapter, HTTP authentication
  middleware, protected-resource metadata and per-request context resolver.
- Configure a durable, tenant-bound `GrantRepository` and revocation backend;
  no in-memory allowlist as a production authority.
- Add durable approvals, protected API-key storage, HTTPS/Traefik origin checks,
  cancellation and operational smoke tests.

Current YC-002/YC-004 keep any remote endpoint disabled until auth/isolation
tests pass. YC-006/008/009/010 remain DRAFT, not approved by this PR.
