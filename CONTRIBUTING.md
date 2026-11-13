# Contributing

Contributions are welcome: YouGile API adapters, MCP tools, workflows, tests,
security reviews and documentation.

## Local development

Python 3.11+:

1. python -m venv .venv
2. Activate .venv (Windows: .venv\Scripts\activate)
3. python -m pip install -e ".[dev]"
4. ruff check .
5. python -m unittest discover -s tests -v
6. python scripts/check_catalog.py

Create a feature branch and a PR linked to the corresponding Linear issue.
Read AGENTS.md before any code change.

## Licensing and attribution

Contributions to original code are submitted under AGPL-3.0-only. You must
have the rights to contribute the code. Never copy code from an upstream
with unknown license, including PR #5 of justrussian/yougile-mcp, without
documented authorization. For imported MIT/AGPL code, preserve required
copyright notices and record the exact upstream commit in
docs/PROVENANCE.md and NOTICE.

Do not include private test data, user identifiers, workspace exports,
credentials or actual API keys.

## Pull request requirements

Every PR must have appropriate tests, documented API assumptions,
security impact, documentation updates and passing CI. Network transport
must fail closed until authentication and authorization pass review.
