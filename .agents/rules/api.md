# YouGile API rules

**When:** touching catalog/, api/client, DTOs, domain operations or API tests.

- The official REST API v2 is the contract; keep the OpenAPI snapshot pinned
  and verify version/freshness when changing operations. Route every endpoint
  through one shared HTTP client.
- Use operationId + method + path and schema as stable mapping; update mapping,
  input validation, output envelope, errors and contract tests in the same PR.
- Never invent endpoints or fields from a tool name. PR #5's 75 registered tools
  are a desired functional inventory, **not** proven working API coverage.
- Differentiate cursor/content pagination from one-page list decoding; test
  multi-page results and explicitly bound iteration and response size.
- Handle 204/no body, 4xx validation errors, 429 and retry-after correctly.
- Do not automatically retry potentially effective POST/PUT writes after a
  timeout without proven idempotency/deduplication.
- Keep company-wide rate limits shared among users and external agents; do
  not let smart/bulk tools bypass the budget.
- A real integration test uses a designated disposable YouGile company, never
  a production project unless separately authorized.
