# VS Code / GitHub Copilot agents

**Transports:** remote Streamable HTTP with OAuth, or local stdio. **Status:** configuration guide; this repository has not completed live VS Code/Copilot E2E.

## Recommended: Copilot harness remote MCP

In current VS Code, use **Chat: Open Customizations → MCP Servers → Add Server**. Choose HTTP and enter `https://YOUR-HOST.example/mcp`. Select the personal or workspace destination and follow the OAuth sign-in flow.

For the **native Copilot harness**, global configuration is `~/.copilot/mcp-config.json` (or `$COPILOT_HOME/mcp-config.json`), and shared project configuration is a workspace-root `.mcp.json` where supported. Example:

~~~json
{
  "mcpServers": {
    "yougile": {
      "type": "http",
      "url": "https://YOUR-HOST.example/mcp",
      "tools": ["*"]
    }
  }
}
~~~

Replace the placeholder URL, authenticate with your YouGile account, select a company if requested, and verify the connection with a read-only tool.

**Do not confuse configuration formats:** older editor-managed `.vscode/mcp.json` files use a top-level `servers` object and belong to the deprecated Local harness; the new portable Copilot configuration uses `mcpServers`. For new setups, use the native harness route above.

The server must accept the exact trusted redirect used by the host. Configure `CLOUD_OAUTH_REDIRECT_ORIGINS` only after observing and verifying that callback; do not loosen the server's redirect policy.

## Local stdio

The Copilot harness also supports an installed local executable. See [local stdio setup](local-stdio.md); configure `type: "stdio"`, an absolute `command` path and protected environment injection. Local runtimes and credentials must exist on the machine where the agent harness actually runs.

Official reference: [VS Code MCP configuration](https://code.visualstudio.com/docs/agents/reference/mcp-configuration).

[Back to client index](README.md)
