# Codex CLI and IDE extension

**Transports:** remote Streamable HTTP with OAuth, or local stdio. **Status:** unverified integration examples for this repository.

## Remote HTTPS (recommended when deployed)

Run:

~~~sh
codex mcp add yougile --url https://YOUR-HOST.example/mcp
codex mcp login yougile
codex mcp list
~~~

Replace the placeholder URL with the **actual** reviewed deployment. The login command starts OAuth; sign in to YouGile and choose the permitted company. In Codex TUI, use `/mcp` to inspect tools and try a read-only call.

Alternatively, add this to `~/.codex/config.toml`:

~~~toml
[mcp_servers.yougile]
url = "https://YOUR-HOST.example/mcp"
~~~

Then run `codex mcp login yougile`. Both CLI and supported IDE Codex integrations can share this configuration. If redirect authorization fails, the operator must allow the exact trusted OAuth callback origin used by Codex; native loopback callbacks are permitted by default.

## Local stdio

Install the server and provision a protected local identity first using [local stdio setup](local-stdio.md). A Codex configuration can launch that preinstalled executable:

~~~toml
[mcp_servers.yougile_local]
command = "/absolute/path/to/yougile-mcp/.venv/bin/yougile-mcp"
args = ["serve"]
[mcp_servers.yougile_local.env]
MCP_TRANSPORT = "stdio"
YOUGILE_COMPANY_ID = "YOUR_COMPANY_ID"
MCP_STDIO_IDENTITY_FILE = "/absolute/private/path/yougile-agent.json"
~~~

The launcher **also** needs `YOUGILE_API_KEY` injected privately into its environment. Do not commit the key in `config.toml` or the identity file. On Windows, use the full path to `.venv\\Scripts\\yougile-mcp.exe`, and a private absolute identity-file path.

## Verify

Use `codex mcp list` and an authorized read-only call. A configured server does not prove that its OAuth callback or tools work end to end.

Official reference: [Codex MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

[Back to client index](README.md)
