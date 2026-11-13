#!/usr/bin/env python3
"""Architecture checks: transport boundary and pinned standards.

This structural guard complements (but cannot replace) behavioral security
and API contract tests. No external packages or network calls.
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_LAYER = Path("src/yougile_mcp/mcp")
FORBIDDEN_NETWORK_IMPORTS = frozenset(
    {"httpx", "requests", "aiohttp", "urllib", "httpcore", "socket"}
)
ENGINEERING_CONTRACTS = frozenset(
    {"YC-006", "YC-007", "YC-008", "YC-009", "YC-010"}
)


def tool_http_import_violations(root: Path = ROOT) -> list[str]:
    """Tool adapters may not implement direct networking."""
    directory = root / MCP_LAYER
    if not directory.exists():
        return []
    failures: list[str] = []
    for file in sorted(directory.rglob("*.py")):
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for module in modules:
                if module.split(".")[0] in FORBIDDEN_NETWORK_IMPORTS:
                    failures.append(
                        f"{file.relative_to(root)}:{node.lineno}: "
                        f"direct networking import {module}; use shared API client"
                    )
    return failures


def standards_violations(root: Path = ROOT) -> list[str]:
    """Require deliberate reviews when independently versioned axes change."""
    manifest = json.loads(
        (root / "docs/references/standards.json").read_text(encoding="utf-8")
    )
    pins = manifest["pins"]
    required = (
        ("mcp_protocol", "version", "2026-07-28"),
        ("openapi_standard", "version", "3.2.1"),
        ("yougile_api", "api_version", "v2"),
        ("yougile_api", "snapshot_oas_version", "3.0.0"),
    )
    failures = []
    for section, field, expected in required:
        actual = pins[section][field]
        if actual != expected:
            failures.append(
                f"version pin changed: {section}.{field} {actual!r} != {expected!r}; "
                "explicit contract and guard revision required"
            )
    if pins["yougile_api"]["snapshot_file"] != "catalog/openapi-operations.json":
        failures.append("invalid vendor catalog source")
    operations = json.loads(
        (root / "catalog/openapi-operations.json").read_text(encoding="utf-8")
    )["operations"]
    operation_ids: set[str] = set()
    routes: set[tuple[str, str]] = set()
    for op in operations:
        identifier = op["operationId"]
        method = op["method"]
        path = op["path"]
        if (
            not isinstance(identifier, str)
            or not identifier
            or method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}
            or not isinstance(path, str)
            or not path.startswith("/api-v2/")
        ):
            failures.append(f"invalid YouGile API operation: {op!r}")
        route = (method, path)
        if identifier in operation_ids or route in routes:
            failures.append(f"duplicate API operation: {identifier}, {route}")
        operation_ids.add(identifier)
        routes.add(route)
    return failures


def contract_violations(root: Path = ROOT) -> list[str]:
    """Require the proposed engineering decision records to exist."""
    failures = []
    for identifier in sorted(ENGINEERING_CONTRACTS):
        found = list((root / "docs/contracts").glob(f"{identifier}-*.md"))
        if len(found) != 1:
            failures.append(f"{identifier}: expected one record, found {len(found)}")
    return failures


def main(root: Path = ROOT) -> int:
    errors = (
        tool_http_import_violations(root)
        + standards_violations(root)
        + contract_violations(root)
    )
    for error in errors:
        print(f"ARCHITECTURE VIOLATION: {error}", file=sys.stderr)
    if errors:
        return 1
    print("Architecture guard passed: boundaries and pinned references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
