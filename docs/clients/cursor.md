# Cursor

**Transports:** remote Streamable HTTP with OAuth, or local stdio. **Status:** connection example; YouGile MCP integration is not yet live-verified.

## Remote HTTPS

Create a global `~/.cursor/mcp.json` or project-local `.cursor/mcp.json`:

~~~json
{
  "mcpServers": {
    "yougile": {
      "url": "https://YOUR-HOST.example/mcp"
    }
  }
}
~~~

Replace the placeholder with the actual HTTPS MCP endpoint. Open Cursor's MCP controls and connect; complete the OAuth browser sign-in to YouGile. Verify tools using a read-only request.

Cursor documents the remote web/agent callback origin `https://www.cursor.com` and local loopback callbacks. The server currently allows native loopback callbacks but **does not include `https://www.cursor.com` by default**. For a Cursor flow using its web callback, the operator must intentionally add the trusted origin to `CLOUD_OAUTH_REDIRECT_ORIGINS`. Do not allow arbitrary origins, and do not include client secrets in a committed `mcp.json`.

## Local stdio

See [local stdio setup](local-stdio.md). Cursor can use `command`, `args` and `env` in `mcp.json` to start the installed `yougile-mcp serve` command. Provide absolute executable and identity paths and privately inject `YOUGILE_API_KEY` into the launched process.

Official reference: [Cursor MCP configuration](https://cursor.com/docs/mcp).

[Back to client index](README.md)
