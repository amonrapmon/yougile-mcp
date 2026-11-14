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
five operations remain outside the PR #5 inventory. All 72 operations now have
per-operation MockTransport coverage; none is marked `live_verified`. Five
operations also have separately recorded owner-run curl observations. The
company PUT was deliberately not sent to a live company. See catalog/ and
docs/PROVENANCE.md.

An importable asynchronous API client currently covers mock-tested read
operations for users, projects and roles, departments, boards, columns, tasks,
stickers, group chats, chat messages and CRM lookup. It also covers create,
update and delete operations across those resources, API-key creation, user
status and chat typing, company listing/detail/update, webhook create/update/
search, multipart file upload and column creation. Company update remains
mock-only; it has not been sent to a live company.
Company listing sends credentials in its documented request body without a
bearer API key. The generic `request(operation_id, path=..., query=...,
body=...)` entry point validates JSON requests and responses against the pinned
OpenAPI contract. The upload method sends immutable bytes as multipart field
`file` through that same client. A hash-pinned compatibility overlay adapts the
six vendor-schema mismatches without changing the official snapshot.

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

async def read_current_user():
    async with YouGileClient(Settings.from_env()) as api:
        return await api.request("UserController_getMe")
```

Protected calls require both `YOUGILE_API_KEY` and `YOUGILE_COMPANY_ID`; a
missing value fails before sending a request. `get_companies` can run before
the company ID is known. The `doctor` command remains offline. `create_column`
is the current write example; its body is validated against the official schema and is tested
only through a fake HTTP transport. Do not use it against a real company
without separate authorization. See `tests/test_api_client.py` for the mocked
write examples.

File uploads use buffered `bytes`, not local paths or streaming input. The
default local policy is 10 MiB and a `text/plain` allowlist; these are client
limits, not verified YouGile limits. Set the constructor options to allow PDF,
image and other MIME types, for example:

```python
async with YouGileClient(
    Settings.from_env(),
    max_upload_bytes=25 * 1024 * 1024,
    allowed_upload_content_types={
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    },
) as api:
    await api.upload_file(
        filename="report.pdf", content=pdf_bytes, content_type="application/pdf"
    )
```

Uploads reject unsafe filenames, content over the configured limit and MIME
types outside the allowlist. A timeout has an uncertain result and is never
retried.

Clients with the same `YOUGILE_COMPANY_ID` share a process-local budget of at
most 50 requests per minute, matching the
[official company limit](https://docs.yougile.com/docs/admin-guide-linux/api/).
Read operations may retry a bounded 429 response when `Retry-After` fits the
wait budget. A write timeout raises an uncertain-write error and is never
retried.

The API client requests `Accept-Encoding: identity` by default. On 2026-11-14
a live read through HTTPX received HTTP 200 but failed while decoding the
response body (`httpx.DecodingError`); requesting an uncompressed response
allowed that same SDK call to succeed. The exact vendor-side compression
problem remains unconfirmed. Uncompressed responses may use more bandwidth,
but this avoids the reproduced failure on the affected YouGile endpoint.

Multiple server replicas need a distributed limiter. `list_all` uses
bounded offset pagination and the task-log timestamp cursor (100 pages and
10,000 items); it raises on a stalled cursor or budget overflow instead of
returning a partial result.

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
