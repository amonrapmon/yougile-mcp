# Implementation patterns and anti-patterns

These are **practical examples**, subordinate to CURRENT contracts in
docs/contracts/. Draft contracts YC-006..YC-010 need maintainer approval
before their detailed design choices become binding.

## MCP transport

**Correct:** use a maintained Python MCP SDK that negotiates supported
protocol revisions; validate authorization per request, enforce scopes
when executing tools, and use SDK-provided wire validation.

**Reject:** copy an old session-first example and build a home-grown
\`initialize\` / \`Mcp-Session-Id\` dependency for every modern 2026 client.
Older clients may require a compatible handshake; verify support before
deciding to remove it. Do not use the presence of an HTTP endpoint alone
as evidence that authentication is implemented.

## REST and OpenAPI

**Correct:**
1. Identify the vendor REST operationId, method, path and schema.
2. Implement/modify the one shared API client operation.
3. Add direct tool adapter with a verified schema and explicit scopes.
4. Add DTO validation, pagination, error and failure tests.
5. Add test-company E2E where possible and document evidence.

**Reject:** infer fields from English names, invent a nonexistent v3
endpoint, or send a blind \`POST\` retry after a timeout.
\`openapi: 3.0.0\` is a description format field, **not** YouGile API v3.

## Tools

**Correct:** smart tools orchestrate canonical API operations with
permission checks on each step, bounded outputs and partial failure
results. Inputs are validated and errors are typed.

**Reject:** an MCP tool importing \`httpx\` or \`requests\` directly;
creating a second YouGile client; applying a guessed schema;
hiding writes inside tools advertised as read-only.

## OAuth and multi-agent

**Correct:** validate issuer, audience, expiry and scopes for each
request and every nested operation; map a principal to an authorized
company server-side and redact credentials in all outputs.

**Reject:** a global shared MCP bearer for all agents, client-provided
tenant IDs that independently grant access, forwarding bearer tokens
to another origin, or unauthenticated Docker port publishing.

## Reliability

**Correct:** classify writes as safe/idempotent/uncertain, honor
company-wide rate limits and \`Retry-After\`; audit outcomes without
leaking task bodies or secrets.

**Reject:** treating a network timeout as proof a write did not happen,
recursively retrying bulk writes, or emitting a success-shaped response
for an unknown vendor error.

## Before opening a PR

- Which CURRENT contract IDs govern the files?
- Is a DRAFT contract relevant? Is approval pending?
- Which vendor/source version was checked?
- Which named edge cases are covered by tests?
- Did the architecture guard pass?
- What was actually run in CI vs only proposed?

## Future UTCP support

**Correct:** keep one protocol-neutral operation registry and a shared
execution service for DTO validation, tenancy, permissions, audit and
reliability. MCP and a future UTCP-backed HTTP surface are independent
presentation/discovery adapters. A UTCP manual can be generated later from
the same canonical schema metadata for securely exposed HTTP endpoints.

**Reject:** publishing a manual containing server-side YouGile credentials,
letting UTCP clients call YouGile directly with privileged shared keys,
duplicating the 75 tools in a separate UTCP implementation, or assuming
every agent harness already supports UTCP.

UTCP is **out of scope for the first release**. Revisit when a real
consumer requires it and the secure HTTP operation gateway is available.
References:
- https://www.utcp.io/docs/
- https://github.com/universal-tool-calling-protocol/utcp-specification
