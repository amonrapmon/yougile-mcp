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
that unlicensed PR has been imported. A pinned OpenAPI snapshot describes 70
REST API v2 operations with five currently unmapped by that PR. See catalog/.

## Verify the foundation

Python 3.11+:

1. Create and activate a virtual environment.
2. Install: python -m pip install -e ".[dev]"
3. Run: python -m yougile_mcp doctor
4. Run: python scripts/check_catalog.py
5. Run: python -m unittest discover -s tests -v
6. Run: ruff check .

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
