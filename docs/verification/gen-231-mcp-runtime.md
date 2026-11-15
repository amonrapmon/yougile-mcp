# GEN-231 · Official Python MCP SDK v2 integration

Follow-up to PR #14 (Tool Factory/Registry/Policy/Dispatcher).

- Uses official `mcp==2.3.0` and its **low-level** SDK `Server`. Dynamic two-handler
  registration preserves schema contents without 72 Python wrappers.
- The full set of 72 tools is registered from `build_registry()`; listing is
  scoped to the authenticated principal for each SDK request.
- Each `tools/call` resolves identity again and calls `ToolDispatcher.call()`.
  Output is structured, validated and bounded. Failures use `is_error=True`
  with sanitized machine-readable category, never raw API messages.
- `Client(server)` integration tests send 72 calls over the official MCP engine
  to real API SDK request handling and `httpx.MockTransport`. No socket or
  YouGile live traffic is required.
- `make_mcp_server()` requires a trusted per-request principal resolver. No
  fallback anonymous identity, no public HTTP listener, no assumed OAuth provider.
- `serve` remains fail-closed until authenticated identity source and
  per-company secret backend have been security reviewed, as required by YC-002/004.
- YC-006/008/009/010 remain DRAFT. This PR does not elevate their authority.

## Owner review required before a public deployment

1. **Tool names & schemas:** recommend adopting `yg_v2_*` and grouped
   `path/query/body` as the initial versioned API; alternatively register
   aliases for historical 75 tool names (requires distinct compatibility plan).
2. **Agent identity:** recommend OAuth 2.1/PKCE for interactive clients with
   issuer/audience/scopes checks, and separately approved service-agent identity.
   No self-signed shared full-access credential.
3. **Project ownership:** project-scoped operations require a trusted, cached
   resource->project resolver. Company-wide endpoints require explicit broad
   access. Cross-company isolation must be verified against actual YouGile
   company ownership and credential provenance.
4. **Approval persistence:** recommend durable single-use store with payload
   digest/actor/operation/expiry, not the local in-memory test ledger for
   replicated services.

These are concrete proposals, not approvals; DRAFT statuses are unchanged.
