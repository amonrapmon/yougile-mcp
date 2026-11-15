# ChatGPT (web)

**Transport:** remote Streamable HTTP with OAuth. **Status:** configuration guide only; YouGile MCP-to-ChatGPT E2E has not yet been verified.

## Prerequisites

- An operational public HTTPS MCP endpoint at `https://YOUR-HOST.example/mcp`. Replace the placeholder with your own deployed server URL.
- A ChatGPT workspace/account with permission to add a **custom MCP server**. Full MCP support for writes is subject to current plan/workspace access. See [OpenAI's availability and permissions](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt).
- Your YouGile credentials for the OAuth sign-in page, and an allowed OAuth redirect origin configured by the server operator.

## Connect

1. In **ChatGPT web**, open **Plugins**.
2. Use **+ → Add custom MCP server** (if your plan and workspace permit it).
3. Enter a display name such as **YouGile MCP**.
4. Under connection, provide `https://YOUR-HOST.example/mcp` (or a supported secure MCP tunnel where applicable).
5. Configure OAuth according to the ChatGPT connection form. Complete the browser sign-in to YouGile; select a company if offered.
6. Accept the security review prompt and create the connection. Inspect the discovered tools before enabling it.
7. Install/select the connection for a conversation (for example with `@`), then make a **read-only** request to verify the company context.

**Do not** enter a `YOUGILE_API_KEY` into ChatGPT or use `http://localhost:8000/mcp` for a hosted ChatGPT connection. ChatGPT does not run this repository's local stdio process from a web chat.

## Limitations

This guide does **not** assert that YouGile MCP is deployed, published in ChatGPT, or live-tested with ChatGPT. Server-side approval-gated operations remain unavailable without a configured approval service, even if ChatGPT requests user confirmation. For available permissions and the current connection UI see [official ChatGPT help](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt).

[Back to client index](README.md)
