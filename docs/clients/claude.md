# Claude web and Claude Desktop

**Transport:** remote Streamable HTTP with OAuth. Claude Desktop's local stdio connections are a separate feature; see [local stdio](local-stdio.md) if you explicitly want a locally run server.

**Status:** integration instructions, not a confirmed live E2E test of YouGile MCP.

## Connect a remote server

1. Open **Customize → Connectors** in Claude (the exact UI can vary by plan).
2. Select **Add custom connector** (or the organization's custom web connector flow).
3. Enter **YouGile MCP** as the name and `https://YOUR-HOST.example/mcp` as its URL.
4. Choose OAuth authentication and the client's supported **automatic registration** option when available. This server implements dynamic client registration; it does not issue a documented static OAuth client ID for this integration.
5. Connect and authenticate in the YouGile sign-in page. Select your YouGile company if asked.
6. Enable the connector in a conversation and verify it with a read-only request.

For Team/Enterprise workspaces, an organization owner may need to add and approve the connector before individual members can connect.

**Important:** Claude's remote connector connects from Anthropic's infrastructure, including when used via Claude Desktop. A private `127.0.0.1` listener will not be reachable. Use a reviewed, publicly reachable TLS deployment (normally port 443). The server default redirect allowlist includes `https://claude.ai` and `https://claude.com`. Verify the exact redirect used by the client.

Official reference: [Custom remote MCP connectors for Claude](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp).

[Back to client index](README.md)
