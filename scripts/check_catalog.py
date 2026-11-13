#!/usr/bin/env python3
"""Offline inventory and operation-to-test binding checks.

SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAPS = {
    "TaskController_getLog",
    "UserController_getMe",
    "ChatMessageController_typing",
    "CrmContactPersonsController_create",
    "CrmExternalIdController_findContactByExternalId",
}
API_TEST_PATH = "tests/test_api_client.py::ApiClientTests."


def _api_test_methods() -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    source = (ROOT / "tests/test_api_client.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    return {
        member.name: member
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "ApiClientTests"
        for member in node.body
        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
        and member.name.startswith("test_")
    }


def _calls_client_method(
    test_method: ast.FunctionDef | ast.AsyncFunctionDef,
    expected_method: str,
    expected_kwargs: dict,
) -> bool:
    for node in ast.walk(test_method):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != expected_method:
            continue
        try:
            actual_kwargs = {
                keyword.arg: ast.literal_eval(keyword.value)
                for keyword in node.keywords
                if keyword.arg is not None
            }
        except (ValueError, TypeError):
            continue
        if all(actual_kwargs.get(name) == value for name, value in expected_kwargs.items()):
            return True
    return False


def _test_binding_errors(operations: list[dict], test_methods: dict[str, ast.AST]) -> list[str]:
    errors = []
    for item in operations:
        if item["status"] not in {"implemented", "mock_tested", "live_verified"}:
            continue
        bindings = item.get("test_bindings", [])
        if not bindings:
            errors.append(f"Covered operation has no test binding: {item['operationId']}")
            continue
        for binding in bindings:
            if not isinstance(binding, dict):
                errors.append(f"Invalid test binding for {item['operationId']}: {binding}")
                continue
            path = binding.get("test_path")
            if not isinstance(path, str) or not path.startswith(API_TEST_PATH):
                errors.append(f"Invalid test binding for {item['operationId']}: {path}")
                continue
            method_name = path.removeprefix(API_TEST_PATH)
            test_method = test_methods.get(method_name)
            if test_method is None:
                errors.append(
                    f"Covered operation test is missing: {item['operationId']} -> {method_name}"
                )
                continue
            client_call = binding.get("client_call")
            kwargs = binding.get("kwargs", {})
            if not isinstance(client_call, str) or not isinstance(kwargs, dict):
                errors.append(f"Invalid operation call binding: {item['operationId']}")
            elif not _calls_client_method(test_method, client_call, kwargs):
                errors.append(
                    f"Test does not call {client_call} for {item['operationId']}: {method_name}"
                )
    return errors


def load(name: str) -> dict:
    return json.loads((ROOT / "catalog" / name).read_text(encoding="utf-8"))


def main() -> int:
    tools = load("tools-75.json")["tools"]
    matrix = load("openapi-operations.json")
    operations = matrix["operations"]
    gaps = set(load("known-gaps.json")["operation_ids"])
    names = {item["name"] for item in tools}
    ids = {item["operationId"] for item in operations}
    spec_path = ROOT / "src/yougile_mcp/api/openapi-v2.json"
    source = json.loads(
        (ROOT / "src/yougile_mcp/api/openapi-source.json").read_text(encoding="utf-8")
    )
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec_operations = {
        (operation["operationId"], method.upper(), path)
        for path, path_item in spec["paths"].items()
        for method, operation in path_item.items()
        if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}
    }
    matrix_operations = {
        (item["operationId"], item["method"], item["path"]) for item in operations
    }

    if len(tools) != 75 or len(names) != 75:
        raise SystemExit("Expected exactly 75 distinct PR #5 tool names")
    if spec.get("openapi") != "3.0.0" or spec.get("info", {}).get("version") != "2.0":
        raise SystemExit("Unexpected YouGile OpenAPI/version axis")
    if hashlib.sha256(spec_path.read_bytes()).hexdigest() != source.get("sha256"):
        raise SystemExit("Pinned official OpenAPI checksum does not match")
    if len(operations) != len(ids) or matrix_operations != spec_operations:
        raise SystemExit("Coverage matrix differs from the pinned official operations")
    if gaps != GAPS or not gaps.issubset(ids):
        raise SystemExit("Known gaps do not match the pinned snapshot")
    if any(item["status"] not in {"discovered", "implemented", "mock_tested", "live_verified", "excluded_with_reason"} for item in operations):
        raise SystemExit("Unknown operation coverage status")
    if any(item["status"] == "excluded_with_reason" and not item.get("notes") for item in operations):
        raise SystemExit("Every excluded operation needs a reason")
    binding_errors = _test_binding_errors(operations, _api_test_methods())
    if binding_errors:
        raise SystemExit("\n".join(binding_errors))
    if any(item["implementation_status"] != "inventory_only" for item in tools):
        raise SystemExit("Foundation catalog must not claim implementation")

    counts = {status: sum(item["status"] == status for item in operations) for status in (
        "discovered", "implemented", "mock_tested", "live_verified", "excluded_with_reason"
    )}
    print(f"Inventory validated: {len(names)} tool names, {len(ids)} official API operations")
    print(f"Coverage statuses: {json.dumps(counts, sort_keys=True)}")
    print(f"Known missing mappings in PR #5: {len(gaps)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
