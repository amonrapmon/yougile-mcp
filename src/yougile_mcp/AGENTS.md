# Python source-specific instructions

Inherits AGENTS.md and CURRENT routed contracts.

- Read .agents/rules/engineering.md, api.md, mcp.md and security.md as
  relevant to changed code.
- One YouGile transport adapter and shared DTO/error handling, with no
  raw HTTP calls from MCP tools.
- Security gates apply to all tool execution, including compound flows.
- No public anonymous transport; reject unsafe configuration by default.
- Maintain Python 3.11 compatibility, typed interfaces, tests and docs.
- If new api/, mcp/, security/ or transport/ subpackages appear, add
  narrower AGENTS.md files at their roots before implementing them.
