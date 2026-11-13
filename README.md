# YouGile MCP

**Open-source · AGPL-3.0-only · self-hosted (in development)**

A planned remote MCP server for YouGile with complete API coverage,
agent-friendly tools, per-agent permissions, and Docker/Traefik deployment.

Project: https://linear.app/amonrapmon/project/yougile-mcp-2e18d5b92b45

> Status: **foundation only**. There are no working YouGile API tools or
> MCP network transport yet. Do not deploy as a public server.

## Functional baseline

The intended surface is the 75 tool names registered by
https://github.com/justrussian/yougile-mcp/pull/5 (commit
6a1c79c3917320a23654681333741d0580c29ba1). No implementation code from
that unlicensed PR has been imported. The pinned official OpenAPI 3.0.0
document describes 72 YouGile REST API v2 operations. The previous 70-operation
snapshot had no removals and lacked two operations added by the official source;
five operations remain outside the PR #5 inventory. The coverage matrix marks
eight operations as mock-tested and the rest as discovered. See catalog/ and
docs/PROVENANCE.md.

An importable asynchronous API client currently covers company listing with
user credentials, board/column/task reads, and a mocked column-creation
operation. Company listing sends its credentials in the documented request
body and does not attach a bearer API key. It is not a complete API SDK;
the other operation IDs are deliberately unavailable in the client until
their request, response and side-effect contracts are implemented and tested.

## API client slice

The client loads its typed operation definitions and runtime DTO validation
from the pinned OAS 3.0.0 source. A normal read uses the API key from
`YOUGILE_API_KEY`:

```python
from yougile_mcp.api import YouGileClient
from yougile_mcp.config import Settings


async def read_boards():
    async with YouGileClient(Settings.from_env()) as api:
        return await api.search_boards({"limit": 50, "offset": 0})
```

Without an API key, protected calls fail before sending a request. The
`doctor` command remains offline. `create_column` is the current write
example; its body is validated against the official schema and is tested
only through a fake HTTP transport. Do not use it against a real company in
this task. See `tests/test_api_client.py` for the mocked write example.

The client defaults to at most 50 requests per minute for one shared client,
matching the official company limit. GET requests may retry a bounded 429
response when `Retry-After` fits the wait budget. A write timeout raises an
uncertain-write error and is never retried. `list_all` uses bounded offset
pagination (100 pages and 10,000 items); it raises on a stalled cursor or
budget overflow instead of returning a partial result.

## Verify the foundation

Python 3.11+:

1. Install uv from <https://docs.astral.sh/uv/>.
2. Install the locked project and development dependencies: `uv sync --locked --all-extras`.
3. Run: `uv run --locked python -m yougile_mcp doctor`.
4. Run: `uv run --locked python scripts/check_catalog.py`.
5. Run: `uv run --locked python -m unittest discover -s tests -v`.
6. Run: `uv run --locked ruff check .`.

Docker:

- docker build -t yougile-mcp:foundation .
- docker run --rm yougile-mcp:foundation
- docker compose --profile verify run --rm config-check

No ports are exposed. The "serve" command deliberately refuses startup until
authenticated transport is implemented.

## Environment

Copy .env.example to .env for Docker Compose interpolation. The Python CLI reads
its process environment, so export values explicitly when testing locally.
Never commit live credentials,
test workspace exports, or secrets. The doctor command reports only booleans
indicating whether credentials are present, never credential values.

## Agent governance (Astryx-inspired)

The canonical entry point is AGENTS.md. Nearest nested AGENTS.md files add
subsystem rules; .agents/rules/ holds cross-cutting constraints,
.agents/workflows/ holds repeatable processes and .agents/skills/ holds
task-specific recipes. Durable behavior lives in docs/contracts/ with
draft/current/archived authority. Only current records are binding.

- python scripts/agent_contracts.py check
- python scripts/agent_contracts.py for src/yougile_mcp/config.py
- python scripts/agent_contracts.py diff origin/main

This arrangement is inspired by the governance model in Meta Astryx
(https://github.com/meta/astryx), but its rules and implementation are original.

## Development contract

Read AGENTS.md, docs/ARCHITECTURE.md, docs/PROVENANCE.md,
docs/ROADMAP.md and CONTRIBUTING.md before opening a PR.

## License

Original code: GNU AGPL-3.0-only (LICENSE). A license declaration on this
repository does not grant rights to copy the unlicensed PR #5 sources.
