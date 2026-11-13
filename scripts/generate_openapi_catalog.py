#!/usr/bin/env python3
"""Regenerate the coverage matrix from the pinned official OpenAPI document.

SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "src/yougile_mcp/api/openapi-v2.json"
SOURCE_PATH = ROOT / "src/yougile_mcp/api/openapi-source.json"
OUTPUT_PATH = ROOT / "catalog/openapi-operations.json"
MOCK_TESTED = {
    "getCompanies",
    "BoardController_search",
    "BoardController_get",
    "ColumnController_search",
    "ColumnController_create",
    "TaskController_search",
    "TaskController_searchReversed",
    "TaskController_get",
}


def schema_sources(value: Any) -> list[str]:
    references: set[str] = set()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            reference = node.get("$ref")
            if isinstance(reference, str):
                references.add(reference)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return sorted(references)


def _effect(operation_id: str, method: str) -> str:
    if method == "GET" or operation_id in {"getCompanies", "AuthKeyController_search"}:
        return "read"
    if method == "DELETE":
        return "destructive"
    return "write"


def _pagination(parameters: list[dict[str, Any]]) -> dict[str, Any] | None:
    names = {parameter["name"] for parameter in parameters}
    if {"limit", "offset"}.issubset(names):
        return {"kind": "offset", "parameters": ["limit", "offset"]}
    if {"limit", "before"}.issubset(names):
        return {"kind": "timestamp_cursor", "parameters": ["limit", "before"]}
    return None


def build_catalog(spec: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for path, path_item in spec["paths"].items():
        for method, operation in path_item.items():
            method = method.upper()
            if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            operation_id = operation["operationId"]
            parameters = operation.get("parameters", [])
            request_body = operation.get("requestBody", {})
            request_schemas = {
                media_type: schema_sources(media.get("schema", {}))
                for media_type, media in request_body.get("content", {}).items()
            }
            responses = {}
            for status, response in operation.get("responses", {}).items():
                responses[status] = {
                    media_type: schema_sources(media.get("schema", {}))
                    for media_type, media in response.get("content", {}).items()
                }
            auth = operation.get("security", spec.get("security", []))
            auth_schemes = sorted({name for requirement in auth for name in requirement})
            rows.append(
                {
                    "operationId": operation_id,
                    "method": method,
                    "path": path,
                    "category": operation.get("tags", [operation_id.split("_", 1)[0]])[0],
                    "parameters": [
                        {
                            "name": parameter["name"],
                            "in": parameter["in"],
                            "required": bool(parameter.get("required", False)),
                            "type": parameter.get("schema", {}).get("type"),
                            "schema_sources": schema_sources(parameter.get("schema", {})),
                        }
                        for parameter in parameters
                    ],
                    "request_schemas": request_schemas,
                    "response_schemas": responses,
                    "pagination": _pagination(parameters),
                    "auth": {"schemes": auth_schemes},
                    "effect": _effect(operation_id, method),
                    "status": "mock_tested" if operation_id in MOCK_TESTED else "discovered",
                    "test_paths": ["tests/test_api_client.py"] if operation_id in MOCK_TESTED else [],
                    "notes": _note(operation_id),
                }
            )
    rows.sort(key=lambda row: row["operationId"])
    return {
        "source": {
            **source,
            "spec_file": "src/yougile_mcp/api/openapi-v2.json",
            "license": source.get("license"),
        },
        "operations": rows,
    }


def _note(operation_id: str) -> str | None:
    if operation_id in MOCK_TESTED:
        return None
    if operation_id in {"CompanyController_get", "CompanyController_update"}:
        return "The vendor path contains a non-standard wildcard with no declared parameter schema."
    if operation_id == "FileController_uploadFile":
        return "Upload limits and allowed MIME types need an approved client policy."
    return "Not included in the first implemented slice."


def main() -> int:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    catalog = build_catalog(spec, source)
    OUTPUT_PATH.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(catalog['operations'])} API operation rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
