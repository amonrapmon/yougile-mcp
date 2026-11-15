# Claude Code

**Transports:** remote Streamable HTTP with OAuth, or local stdio. **Status:** configuration guide; real YouGile MCP interoperability has not been verified.

## Remote HTTPS

~~~sh
claude mcp add --transport http yougile https://YOUR-HOST.example/mcp
claude mcp list
~~~

Replace the placeholder with your own deployed endpoint. In Claude Code run `/mcp` to inspect the server and complete its OAuth browser sign-in. The YouGile login screen authenticates the individual account; select a company when asked. Verify using a harmless read operation.

The cloud OAuth server already permits loopback native-client callbacks, as well as approved Claude web origins. A different callback must be explicitly allowlisted by the server operator.

## Local stdio

Follow [local stdio setup](local-stdio.md) to install the server, securely inject `YOUGILE_API_KEY`, and create the per-agent identity file. Then configure a local server with a command like:

~~~sh
claude mcp add --transport stdio yougile-local -- /absolute/path/to/yougile-mcp/.venv/bin/yougile-mcp serve
~~~

The server process **must inherit** `MCP_TRANSPORT=stdio`, `YOUGILE_COMPANY_ID`, `YOUGILE_API_KEY` and `MCP_STDIO_IDENTITY_FILE` from a private trusted launcher/environment. Simply adding a command without those settings will fail closed. On Windows, use the installed `.venv\\Scripts\\yougile-mcp.exe` path. You can alternatively use Claude Code's `--env` options for **nonsecret** values.

Check `claude mcp list` or `/mcp` and test a read-only operation.

Official reference: [Claude Code MCP](https://code.claude.com/docs/en/mcp).

[Back to client index](README.md)
