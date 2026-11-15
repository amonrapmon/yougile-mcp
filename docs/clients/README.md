# Connect an AI client

YouGile MCP currently provides two distinct transports:

| Transport | Intended clients | Credentials | Availability |
| --- | --- | --- | --- |
| **Remote Streamable HTTP** | ChatGPT, Codex, Claude, Cursor, VS Code Copilot | OAuth sign-in with an individual YouGile account | Implemented as a **private-loopback pre-release service**; public deployment and real client E2E remain release gates |
| **Local stdio** | Locally launched MCP agents (for example Codex CLI and Claude Code) | Company-scoped YouGile API key and a private per-agent identity file | Implemented; requires explicit operator setup |

There is **no published production YouGile MCP endpoint** in this repository. Examples below use `https://YOUR-HOST.example/mcp` as a placeholder, **not a usable service URL**. The host must first be deployed behind reviewed HTTPS and be accessible to the selected client.

## Client-specific guides

| Client | Guide | Recommended transport |
| --- | --- | --- |
| ChatGPT (web) | [ChatGPT](chatgpt.md) | Remote HTTPS + OAuth |
| Codex CLI / IDE | [Codex](codex.md) | Remote HTTPS + OAuth; local stdio also supported |
| Claude Code | [Claude Code](claude-code.md) | Remote HTTPS + OAuth; local stdio also supported |
| Claude web / Desktop | [Claude](claude.md) | Remote HTTPS + OAuth |
| Cursor | [Cursor](cursor.md) | Remote HTTPS + OAuth; local stdio supported |
| VS Code / GitHub Copilot | [VS Code](vscode.md) | Remote HTTPS + OAuth; local stdio supported |
| Locally installed agents | [Local stdio](local-stdio.md) | Local stdio |

## Remote connection prerequisites

1. A server operator has deployed and verified an authenticated public HTTPS reverse proxy for the cloud application, with the MCP endpoint at `https://YOUR-HOST.example/mcp`. **The checked-in Dockerfile and compose.yaml do not deploy or publish this endpoint.**
2. You have a YouGile account permitted to access the selected company; OAuth uses that person's account, not a shared global API key.
3. The OAuth redirect origin used by the client is permitted by the server. The default includes `https://claude.ai` and `https://claude.com`, as well as loopback native-client callbacks. The operator can explicitly allow additional known callback origins or app schemes via `CLOUD_OAUTH_REDIRECT_ORIGINS`. **Do not add wildcard or untrusted origins.**
4. Authenticate in the client's browser-based OAuth flow and choose a company when prompted. Do not enter your YouGile password into an MCP JSON configuration.

## Current capability and safety boundaries

- The server registers descriptors for the 72 official YouGile REST API v2 operations; some may be unavailable at execution time due to policy, permissions or missing approval/credential providers. Registration is not a guarantee that every write is executable.
- Cloud access is **Full Access within the signed-in user's YouGile account and selected company**, not a customizable project-scoped RBAC product. Sensitive actions that require server-side approval currently fail closed without an approval provider.
- MCP clients may ask for user confirmation for write actions. Such UI confirmations do not automatically satisfy server-side approval requirements.
- The vendor live verification matrix and real ChatGPT/Codex/Claude/Cursor/VS Code interoperability are separate. Follow [release verification](../verification/gen-229-live-e2e.md); do not present these example configurations as tested E2E.
- A tool list appearing in an AI client proves discovery, not authorization of a particular write. Test with harmless read operations first.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| HTTP connection fails | Ensure the server is actually deployed behind trusted HTTPS, correct `/mcp` path, valid TLS and external reachability |
| OAuth reports invalid redirect | Have the operator inspect the **exact** callback origin and configure `CLOUD_OAUTH_REDIRECT_ORIGINS` for that trusted client; do not disable redirect validation |
| Login succeeds, but no tools | Check company/account state, OAuth token validity and server access. Inspect sanitized server logs |
| Tool returns `permission_denied` or `approval_required` | Check YouGile permissions and the server-side dispatcher policy, not just the client's confirmation dialog |
| Remote client attempts local `127.0.0.1` | Hosted AI clients cannot access the server operator's loopback address. Use reviewed HTTPS deployment or the client's supported private-tunnel mechanism |
| Local stdio fails to start | See [local stdio](local-stdio.md), including environment, protected identity file and OS ownership checks |

Official client documentation is linked inside each guide. Client UI and command syntax may change independently from this project.
