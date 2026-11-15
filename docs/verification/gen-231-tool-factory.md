# GEN-231 · Universal Tool Factory (internal contract layer)

72 Direct Tool descriptors are compiled from the verified compatible OAS 3.0
snapshot via one registry. They are **not** 72 independently maintained Python
functions. A new operation without an explicit policy entry fails registration.

- MCP names: provisional pattern `yg_v2_<operationId in snake_case>`, not yet a
  published compatibility contract (YC-010 is DRAFT).
- Arguments: optional `path`, `query`, `body` objects when defined by OAS. Multipart
  uses a restricted `multipart_file` with base64 bytes and no filesystem paths.
- Protected auth-key and password operations have **no caller-controlled credentials**
  in their input schemas. Their fields are resolved from a server-side vault
  and their credential-bearing outputs are redacted.
- Response: `{status_code, data}` with validated, operation-specific successful
  DTOs. For known auth-key return shapes the data is redacted by policy.
- Effects/scopes: explicit reviewed-in-PR per-operation `policy-manifest.json`,
  not inferred at invocation from HTTP verbs. Elevated deleted/restore changes
  are checked again when the payload contains the top-level `deleted` property.
- All invocations require an authenticated company-bound principal, operation
  scope, verified project resolver for project resources or explicit company-wide
  privilege, and one-shot approval for protected operations.
- Audit only contains actor, bound company, operation and sanitized outcome.

## Security gate

This PR intentionally does NOT expose a public server or add an SDK handler.
The principal issuer, project ownership resolver, approval service, and server
vault are integration interfaces. A fake resolver is suitable for mock tests but
**not** evidence of live cross-tenant isolation. Remote MCP depends on GEN-218,
GEN-219 and approval of the applicable DRAFT contracts.

The v2 official Python SDK is available (v2.3.0 observed 2026-11-15) and supports
direct dynamic list/call handlers. Install/pin + uv.lock update and transport
integration belong in the runtime PR, after deciding the public tool contract;
do not add an unverified dependency to a locked build.
