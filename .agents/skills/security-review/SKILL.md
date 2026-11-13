---
name: security-review
description: Review authentication, remote MCP, scopes, token handling and write safety.
---

# Security review

Use when editing OAuth, token parsing, public transport, scopes, file uploads,
SSRF boundaries, permission filtering, destructive tools or audit.

1. Identify trust boundaries: agent, MCP server, company, YouGile REST API.
2. Inspect all callers, including smart tools and background workflows.
3. Confirm principal, tenant, audience, expiry and revoke checks.
4. Test that a user cannot select a foreign company or infer its resources.
5. Confirm failed requests and partial writes are audited without secrets.
6. Check replay, unsafe retries, approvals, malicious task text, file
   traversal, SSRF and outbound redirect handling.
7. Run focused tests and document residual risks. No public network exposure
   unless access-control tests pass.
