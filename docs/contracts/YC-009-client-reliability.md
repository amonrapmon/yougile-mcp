---
id: YC-009
authority: draft
owner: maintainer
applies_to: ["src/yougile_mcp/**", "tests/**", "catalog/**", "docs/references/**"]
superseded_by: null
---

# YC-009: API reliability, bulk actions and observability

## Intent

The client respects YouGile company limits, distinguishes safe retries from
potential duplicate side effects and produces inspectable operation outcomes.

## Invariants

- **YC-009/INV1:** A company-wide limiter budgets all agents, retries,
  nested workflows, read and write calls. Replicas cannot independently
  multiply the intended request budget.
- **YC-009/INV2:** Timeouts and disconnects after a possible write produce
  an indeterminate result unless safe idempotency or deduplication is proven;
  the client never assumes a failed response means no mutation happened.
- **YC-009/INV3:** Retry backoff applies to known transient failures,
  429/Retry-After and explicitly idempotent operations. Hard retries have
  a bounded budget and do not defeat user cancellation.
- **YC-009/INV4:** Bulk and compound tools define max operation count,
  partial success, per-item errors and a clear safe rerun strategy.
- **YC-009/INV5:** File upload/download methods apply size/MIME limits,
  stream where possible, guard against arbitrary local path access, and
  protect credentials against SSRF/redirect exfiltration.
- **YC-009/INV6:** Audit/trace records use a stable actor, company, operation,
  request correlation ID, decision, duration and outcome without raw
  credentials or sensitive message content.
- **YC-009/INV7:** API errors have stable machine-readable categories
  distinct from end-user summaries; unknown errors are not silently
  interpreted as success.

## Non-goals

This record does not establish a particular rate-limit numeric value
without vendor evidence or force Redis/PostgreSQL into single-instance
development. It does not permit unbounded bulk actions.

## Verification

Deterministic simulated 429/timeout/5xx/partial success cases, duplicate
side-effect tests, multi-agent concurrency tests, file path rejection,
secret-redaction assertions and controlled disposable-company E2E.
