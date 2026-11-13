# MCP tool authoring rules

**When:** changing MCP tool definitions, catalog or smart/compound tools.

- Every tool has a single purpose, validated input/output schemas, stable
  errors, explicit read/write/destructive classification and scopes.
- Both direct operations and smart tools use the same API adapter, policy,
  rate limiting and audit. Tool discovery filtering does not grant permission.
- Low-level API parity and high-level convenience tools coexist. Do not
  silently remove PR #5's historical 75 functional scenarios.
- Use consistent names, descriptions, argument defaults, pagination, size
  budgets, and structured response metadata. Avoid unbounded tool output.
- Treat tool names, schemas and defaults as public compatibility surfaces.
  Any breaking change requires a current contract decision and migration notes.
- Smart workflows may issue multiple REST requests; plan side effects,
  partial failure, retries and approval boundaries before writing code.
- Never return raw API keys, access tokens, entire confidential files or
  privileged data a principal cannot access.
- Do not enable remote transport based solely on tool registration.
