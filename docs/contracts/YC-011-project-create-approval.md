---
id: YC-011
authority: draft
owner: maintainer
applies_to: ["src/yougile_mcp/mcp/**", "tests/test_mcp_*.py", "docs/ARCHITECTURE.md"]
superseded_by: null
---

# YC-011: Payload-sensitive approval for ordinary project creation

## Intent

Permit an authenticated actor with company-wide YouGile project-admin scope
to create an ordinary project without a second MCP-server approval **only**
when the payload cannot change project memberships or permissions.
Keep all other administrative and destructive actions fail-closed.

This record is a DRAFT for maintainer review before the behavior becomes a
published security contract. The implementation in GEN-271 is a proposed change,
not evidence of approval or live deployment.

## Invariants

- **YC-011/INV1:** Only `ProjectController_create` with exactly a `body`
  containing a nonblank `title` and optional `idempotencyKey` is eligible
  for direct execution. Omitted fields and explicitly present empty
  `users`/`departments` are different payloads; the latter stay protected.
- **YC-011/INV2:** The direct path still verifies authenticated principal,
  operation scope `yougile.projects.admin`, company-wide binding, input schema
  and trusted YouGile company identity. Vendor user permissions are not bypassed.
- **YC-011/INV3:** If any membership, department or other field is supplied,
  the existing one-time actor/company/operation/payload-bound approval applies.
  In the absence of a trusted server approval service, return
  `approval_required` before making a project-creation API request.
- **YC-011/INV4:** The exception is declared in a reviewed central policy
  manifest, and its precise allowed fields and single operation are validated
  when the tool registry is built. Unknown exemptions are configuration errors.
- **YC-011/INV5:** No changes to authentication, company choice, user/role
  management, credential operations, webhooks, upload approvals, destructive
  updates or automatic permission escalation are authorized by this record.

## Non-goals

This decision does not implement the general durable server approval workflow,
does not change the identity model, and does not assert that all 72 listed
tools can be invoked without additional prerequisites. It does not turn a
ChatGPT plugin permission toggle into trusted approval evidence.

## Verification

MockTransport end-to-end tests must show a title-only POST succeeds through
the real dispatcher and cloud MCP with no approval provider, for the
right company-bound credentials. Negative cases include other company,
missing scope, non-company-wide principal, membership/department fields
(including empty objects), blank title, reuse of a one-time approval and
different payloads. Security-regression checks confirm no other operation
gains a direct-write exemption. A production YouGile write is a separate
opt-in live validation after deployment.
