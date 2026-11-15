# Roadmap and release gates

YouGile MCP remains a **pre-release** project. This page distinguishes the original implementation backlog from the current state. See [Architecture](ARCHITECTURE.md) and the [client guides](clients/README.md) for the behavior in the checked-in code.

## Implemented baseline (as of 2026-11-15)

- Official 72-operation REST API v2 catalog, schema-driven client and direct MCP tool descriptors.
- Authenticated local stdio runtime with private per-agent identity.
- OAuth-backed Streamable HTTP application that binds to loopback, with company-bound individual YouGile credentials.
- PostgreSQL and Valkey integration, company administrator UI and separately allowlisted host operator UI.

An operation being registered or mock-tested does not mean its default hosted execution path is authorized. Server-side approval-gated actions still require an approval provider.

## Before public release

1. Review and deploy trusted HTTPS termination, reverse-proxy routing and public origin/header handling; do not expose the loopback HTTP server directly.
2. Test real client interoperability and OAuth callback flows for ChatGPT, Codex, Claude, Cursor and VS Code, documenting the exact supported versions and redirect origins.
3. Complete disposable-company vendor E2E and reconcile documented failures or blocked cases. See [GEN-229 live report](verification/gen-229-live-e2e.md).
4. Decide and implement production-ready server-side approvals, credential-dependent operation policy and shared per-company rate limiting if running multiple replicas.
5. Resolve distribution rights for the pinned vendor OpenAPI document before publishing release artifacts. See [PROVENANCE](PROVENANCE.md).
6. Review security, migrations, deployment/rollback procedure, secrets and administration permissions, then publish supported deployment documentation.

## Historical implementation issue index

The initial planning track in [Linear](https://linear.app/amonrapmon/project/yougile-mcp-2e18d5b92b45) used GEN-211 through GEN-221 for license/provenance, repository and CI foundation, API inventory, client contracts, agent-oriented tools, OAuth, security, deployment and live tests. Those issue names described **work to be performed at the time**, not present-day status guarantees. Subsequent GEN-229 and GEN-231 verification/hosting work is documented separately.

New features and their completion status should be tracked in Linear, with verified public behavior reflected in this roadmap and the architecture document.
