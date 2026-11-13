# Security policy

The repository is in the foundation stage. It does **not** provide a
publicly deployable remote MCP server.

## Reporting security issues

Do not report credentials, personal data or exploitable details in public
issues. Use private GitHub channels to contact the maintainers.

## Mandatory properties for future features

- Independently identified principals for each remote agent/client.
- No API key values or passwords in MCP tool outputs or logs.
- Authorization on every read/write execution, including compound tools.
- Public HTTP listener disabled until OAuth / scoped auth implementation.
- No credentials or data dumps committed to the repository.
- Non-idempotent operations cannot be automatically retried without a safe
  deduplication contract.
- Rate limit shared by company, across agent sessions.
- Uploads bounded by content type and size. No arbitrary local host paths.
- YouGile content is untrusted model input.
