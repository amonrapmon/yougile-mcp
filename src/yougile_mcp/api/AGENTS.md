# Shared YouGile API client

Inherits the repository AGENTS.md and the current contracts routed to
`src/yougile_mcp/api/**`.

- This package is the only YouGile HTTP client. Keep it independent of MCP
  SDKs and tool registration.
- Use only operation IDs and schemas from the pinned official OpenAPI source.
- Do not retry writes after a timeout or forward credentials across redirects.
- Keep credentials out of representations, logs, exception messages and tests.
- Keep pagination bounded and preserve cancellation.
