<p align="right"><a href="README.md">Русский</a> · <strong>English</strong></p>

<h1 align="center">YouGile MCP</h1>

<p align="center"><strong>Connect AI agents to YouGile through the Model Context Protocol</strong></p>

<p align="center">One MCP server for tasks, projects, people, and other YouGile REST API v2 capabilities.</p>

<p align="center">
  <a href="https://github.com/amonrapmon/yougile-mcp/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/amonrapmon/yougile-mcp/actions/workflows/ci.yml/badge.svg?branch=main"></a>
  <a href="LICENSE"><img alt="AGPL-3.0" src="https://img.shields.io/badge/license-AGPL--3.0-0f766e"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11%2B-3776AB">
  <img alt="72 REST API v2 operations" src="https://img.shields.io/badge/REST%20API%20v2-72%20operations-555e75">
  <img alt="Pre-release" src="https://img.shields.io/badge/status-pre--release-a16207">
</p>

<p align="center">
  <a href="#capabilities">Capabilities</a> ·
  <a href="#connect">Connect</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#documentation">Documentation</a>
</p>

---

> [!IMPORTANT]
> **Preparing for public release.** Authenticated local stdio and a private OAuth-backed Streamable HTTP server are implemented. Public HTTPS deployment and real-client interoperability testing are still in progress. There is no published production endpoint yet.

## Capabilities

### Workspace

**Projects, boards, and columns:** read and update the workspace structure through the official REST API.

**Tasks:** search, view, create, and edit tasks and related data.

### People and communication

**Users, roles, and departments:** supported employee and organization operations.

**Chats and messages:** group chat and message operations.

### Integrations and administration

**CRM, files, and webhooks:** supported CRM operations, file uploads, and webhook management.

**MCP access administration:** employee connections, access revocation, blocking, and a separate host-operator console.

<details>
<summary><strong>What does support for 72 API operations mean?</strong></summary>

The server registers **72 direct MCP tool descriptors** derived from the official YouGile REST API v2 operations. This does not mean 72 agent-friendly compound workflows. High-level agent tools are a separate development track.

Tool discovery does not guarantee execution. User permissions, server policy, and required approvals are checked on every call. Operations requiring unavailable approval or secret-injection providers fail closed.

More: [architecture](docs/ARCHITECTURE.md) · [live API verification](docs/verification/gen-229-live-e2e.md) · [API provenance](docs/PROVENANCE.md).

</details>

## Connect

Choose the transport according to where your AI client runs.

### Remote server · Streamable HTTP + OAuth

For ChatGPT, Codex, Claude, Cursor, and VS Code. Each person signs in with their own YouGile account and selects a company. Example address after a reviewed HTTPS deployment:

`https://YOUR-HOST.example/mcp`

**Client guides** (currently available in Russian)

[ChatGPT](docs/clients/chatgpt.md) ·
[Codex CLI / IDE](docs/clients/codex.md) ·
[Claude Code](docs/clients/claude-code.md) ·
[Claude Web / Desktop](docs/clients/claude.md) ·
[Cursor](docs/clients/cursor.md) ·
[VS Code / GitHub Copilot](docs/clients/vscode.md)

> The URL above is a placeholder, not a hosted service. The current Dockerfile and Compose configuration do not publish an MCP endpoint.

### Local server · stdio

For agents running an MCP child process on the user's computer. Requires a company-scoped YouGile API key, company ID, and private per-agent identity file.

**[Local stdio setup →](docs/clients/local-stdio.md)** (in Russian)

For transport comparison, OAuth requirements, and troubleshooting, see the **[client guide index](docs/clients/README.md)**.

## Quick start

Install **Python 3.11+** and [uv](https://docs.astral.sh/uv/).

~~~bash
git clone https://github.com/amonrapmon/yougile-mcp.git
cd yougile-mcp

uv sync --locked --all-extras
uv run --locked yougile-mcp doctor
~~~

The `doctor` command validates configuration **offline** without contacting YouGile. To run a working local MCP server, configure credentials and the identity file as described in the [stdio guide](docs/clients/local-stdio.md).

<details>
<summary><strong>Catalog checks, tests, and linting</strong></summary>

~~~bash
uv run --locked python scripts/check_catalog.py
uv run --locked python -m unittest discover -s tests -v
uv run --locked ruff check .
~~~

The complete developer verification workflow is described in [AGENTS.md](AGENTS.md).

</details>

## Architecture

~~~mermaid
flowchart LR
    L["Local AI agents"] --> S["stdio"]
    R["Remote AI clients"] --> H["Streamable HTTP + OAuth"]
    subgraph MCP["YouGile MCP"]
        S --> T["Tool registry"]
        H --> T
        T --> P["Authorization · policy · validation"]
        P --> C["Unified API client"]
    end
    C --> Y["YouGile REST API v2"]
~~~

Both transports share the same tool registry and API client. Each invocation checks the actor, company, permissions, and resource ownership. Errors are normalized, and credentials are never returned in tool results.

Cloud OAuth is bound to each person's YouGile permissions. Configurable per-project OAuth access is not implemented. PostgreSQL and Valkey hold cloud authorization/connection state; company administration and host-operator administration are separate trust boundaries.

**[Architecture and security boundaries →](docs/ARCHITECTURE.md)**

## Documentation

**Connecting and operating**  
[AI clients](docs/clients/README.md) · [Local stdio](docs/clients/local-stdio.md) · [Architecture](docs/ARCHITECTURE.md)

**Capabilities and verification**  
[Live API verification](docs/verification/gen-229-live-e2e.md) · [Administration verification](docs/verification/gen-231-indalo-company-admin.md) · [Roadmap](docs/ROADMAP.md)

**Development and licensing**  
[Contributing](CONTRIBUTING.md) · [Agent rules](AGENTS.md) · [Contracts](docs/contracts/README.md) · [Provenance](docs/PROVENANCE.md)

---

<sub>Original code is licensed under <a href="LICENSE">GNU AGPL-3.0-only</a>. Adapted Indalo modules preserve their attribution. Third-party licensing and the vendor OpenAPI snapshot distribution review are recorded in <a href="docs/PROVENANCE.md">PROVENANCE.md</a>.</sub>
