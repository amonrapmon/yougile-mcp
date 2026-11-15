[Русский](README.md) | **English**

# YouGile MCP

**An open-source Model Context Protocol server for YouGile.**

Connect MCP-compatible AI clients to your YouGile workspace with direct access to the official REST API v2 through authenticated local or remote transports.

**Status:** pre-release · **License:** [AGPL-3.0-only](LICENSE) · **Runtime:** Python 3.11+ · **API catalog:** 72 official REST v2 operations

> **Not yet a public hosted service.** Local authenticated stdio and the private OAuth-backed Streamable HTTP shell are implemented. Public HTTPS deployment, actual AI-client interoperability and selected live/vendor checks are still release gates. There is no published production endpoint to paste into an AI client.

## Overview

YouGile MCP exposes API-backed tools for reading and changing YouGile data within a selected company. Both transports share the same OpenAPI-driven tool registry, validated API client, authorization checks and structured errors. Client configurations are provided for popular AI agents, but live interoperability is not yet certified.

## Functionality

| Area | Direct REST v2 coverage |
| --- | --- |
| **Projects and workspace** | Projects, boards, columns, organizational structure |
| **Tasks** | Task search, reading and mutations, task-related metadata |
| **Users and access** | Users, roles, departments, account and company operations |
| **Communication** | Group chats and messages |
| **Files** | Multipart upload through the API client, with additional MCP input limits |
| **CRM** | Contact and other available CRM endpoints |
| **Integrations** | Webhook management and supported API operations |
| **Administration** | Company user sessions, disconnect/block controls and a separate host operator panel |

The server registers **72 direct tool descriptors** from the official OpenAPI catalog; this is API parity, **not** 72 high-level AI workflows. Access depends on the authenticated YouGile account and server policy. Approval-gated/destructive or credential-dependent operations may reject calls when the required server-side provider is not present. The direct tool layer currently should not be described as a completed smart task/bulk-operation framework.

For implementation details, see [Architecture](docs/ARCHITECTURE.md), [API provenance](docs/PROVENANCE.md) and [live verification](docs/verification/gen-229-live-e2e.md).

## Connection options

| Mode | Typical client | Authentication | Status |
| --- | --- | --- | --- |
| **Remote MCP** | ChatGPT, Codex, Claude, Cursor, VS Code | OAuth sign-in, personal YouGile account | Private-loopback implementation; public deployment / client E2E pending |
| **Local MCP** | Locally running coding agents | Per-agent identity file plus company-scoped API key | Implemented, requires trusted manual provisioning |

**Installation and setup guides (currently in Russian):**

- [ChatGPT](docs/clients/chatgpt.md)
- [Codex CLI / IDE](docs/clients/codex.md)
- [Claude Code](docs/clients/claude-code.md)
- [Claude web / Desktop](docs/clients/claude.md)
- [Cursor](docs/clients/cursor.md)
- [VS Code / GitHub Copilot](docs/clients/vscode.md)
- [Local stdio installation](docs/clients/local-stdio.md)

See the [client compatibility and prerequisites index](docs/clients/README.md) before connecting. Example remote addresses are placeholders, not public YouGile MCP hosting URLs.

## Local developer quick start

Requirements: Python 3.11+ and [uv](https://docs.astral.sh/uv/).

~~~sh
git clone https://github.com/amonrapmon/yougile-mcp.git
cd yougile-mcp
uv sync --locked --all-extras
uv run --locked yougile-mcp doctor
uv run --locked python scripts/check_catalog.py
uv run --locked python -m unittest discover -s tests -v
~~~

The `doctor` command validates configuration **offline**, without connecting to YouGile. To actually launch local MCP, provision a private agent identity and credentials, then start `yougile-mcp serve` according to the [stdio guide](docs/clients/local-stdio.md). Do not place real API keys in committed configuration or documentation.

The Docker image and `compose.yaml` currently provide an offline verification scaffold, **not** a deployable public MCP endpoint.

## Architecture and access

- One schema-validated YouGile API v2 client backs both transports.
- Direct MCP tools use per-operation policy, actor/company checks and sanitized errors.
- Remote OAuth uses individual YouGile sign-in, company selection, encrypted persistence in PostgreSQL and ephemeral state in Valkey.
- The hosted UI provides company-level administration and a separate allowlisted host-operator area.
- Cloud access is currently **Full Access within the signed-in user's own YouGile permissions**, not granular per-project OAuth scopes. Sensitive operations lacking a configured approval/secret provider fail closed.
- Public remote traffic must pass through a separately reviewed HTTPS reverse proxy; the current cloud process binds to loopback.

Read the [architecture and release boundaries](docs/ARCHITECTURE.md) and the [administration verification notes](docs/verification/gen-231-indalo-company-admin.md).

## Documentation

| Topic | Reference |
| --- | --- |
| Client connection | [AI client installation guides](docs/clients/README.md) |
| Architecture | [Architecture](docs/ARCHITECTURE.md) |
| Live API validation | [GEN-229 verification](docs/verification/gen-229-live-e2e.md) |
| API provenance and legal attribution | [Provenance](docs/PROVENANCE.md) |
| Engineering roadmap | [Roadmap](docs/ROADMAP.md) |
| Agent development rules | [AGENTS.md](AGENTS.md) and [contracts](docs/contracts/README.md) |
| Contributions | [Contributing](CONTRIBUTING.md) |

## Development and licensing

Contributions must follow [CONTRIBUTING.md](CONTRIBUTING.md) and the repository's [AGENTS.md](AGENTS.md). Original code is released under **GNU AGPL-3.0-only**. Adapted Indalo components retain their required notices and attribution. A license on this project does **not** authorize copying unlicensed third-party implementation code; see [PROVENANCE.md](docs/PROVENANCE.md). The redistribution status of the pinned vendor OpenAPI document remains a release review item.
