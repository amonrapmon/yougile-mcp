---
id: YC-012
authority: current
owner: maintainer
applies_to: ["src/yougile_mcp/mcp/**", "tests/test_mcp_*.py", "docs/ARCHITECTURE.md"]
superseded_by: null
---

# YC-012: Safe self-membership for a project without participants

## Intent

Allow a verified **company administrator** to make a newly created empty
YouGile project visible by assigning only themselves as its first
project administrator, without introducing a general privilege-management
bypass. Also allow creating a project with that single self-assignment.

This maintainer-approved exception supplements current YC-011. It does not
authorize other users, inherited teams, or elevated roles. The contract is
approved independently of deployment and live verification.

## Invariants

- **YC-012/INV1:** MCP caller-supplied IDs are never trusted as the actor.
  The execution-bound YouGile credential must return
  `UserController_getMe` with `isAdmin: true`, a nonblank user ID and
  `messengerOnly` not true. Company identity must already have been checked
  using the authenticated company-bound API client.
- **YC-012/INV2:** The only allowed unapproved creation payload is a
  nonblank `title`, an optional `idempotencyKey`, and exactly one `users`
  entry mapping the verified current YouGile user to `"admin"`. The
  separate YC-011 title-only creation exception remains unchanged.
  No `departments`, additional users, other role, or unknown fields are
  exempt.
- **YC-012/INV3:** The only allowed unapproved update is a project path ID
  and a body with exactly `users:{verifiedUserId:"admin"}`. Before the
  update, `ProjectController_get` must verify the same project ID, no
  deletion, and no existing users/departments. Missing users/departments
  may mean empty; any nonempty configuration denies the exception.
- **YC-012/INV4:** All existing company-wide scope, resource-ownership,
  schema and vendor-permission checks remain in force. A valid trusted
  payload-bound approval may still authorize a broader change, but this
  exception never does.
- **YC-012/INV5:** Any failure in the company, current-user or project
  lookup causes denial; the server must not log tokens or use a user ID from
  a tool argument as an authority claim.
- **YC-012/INV6:** The exception does not modify company roles, project
  members after their first assignment, arbitrary project roles, users,
  secrets, deletion, webhooks, departments or unowned projects.

## Non-goals

No general approval workflow is implemented by this exception (GEN-219).
No auto-assignment of all company employees. No changes to completed
projects that already contain permissions.

## Verification

Cloud MCP integration and unit MockTransport tests: successfully add the
verified admin once; reject second attempt, any other actor/role, an
existing member/department, cross-company access, non-admin actor,
deleted project, extra write fields, and unavailable vendor identity.
Check the ordinary 72-operation dispatcher path still works. Re-test
visibility in the actual YouGile UI after deployment.
