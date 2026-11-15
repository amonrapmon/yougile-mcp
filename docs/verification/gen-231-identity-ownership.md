# GEN-231 · Provider-verified company and project lineage

This stage hardens internal authorization without enabling any transport.

- `CompanyIdentityVerifier` calls **the canonical YouGile API client** to confirm
  that the configured company credential actually identifies the expected
  provider-side company. Positive results are cached for at most 60 seconds
  within one client instance. Errors and mismatches deny access.
- `ProjectOwnershipResolver` resolves trusted project IDs by walking
  board → project, column → board → project and task → column → board → project.
  Source and destination projects must both be allowed for moves.
- Both guards are injected into the existing `ToolDispatcher`; no duplicate
  HTTP implementations and no per-operation MCP handlers.
- Invalid inputs are rejected before any ownership traversal; no unvalidated
  tool argument can trigger project-resolution traffic.
- Chats and stickers are company-global in the compatible vendor DTOs and
  have no provable project relation, so their tools require explicit
  `company_wide` grants. They are **never** authorized by guessing a project.

## Limits

A mere company ID in an incoming principal does not establish an agent's
membership. The identity provider must issue cryptographically verified
tokens bound to the agent, company and project grants. The final remote MCP
deployment MUST configure both the company verifier and the project resolver
and independently verify token issuer, audience, expiry and grants.

This PR does not implement an OAuth issuer, open any public port, approve
DRAFT contracts or claim cross-tenant live E2E. Remote identity issuance,
client registration, and a durable approvals backend require owner decisions.
