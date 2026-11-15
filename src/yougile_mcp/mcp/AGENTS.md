# MCP layer

Inherits repository and source AGENTS.md and CURRENT YC-001..YC-005.

- Never implement direct HTTP; use YouGileClient.request().
- Only approved contracts authorize public exposure; DRAFT does not.
- Fail closed without verified principal/company/project ownership.
- Keep credentials and approval evidence server-side; no secrets in tool arguments/results/logs.
