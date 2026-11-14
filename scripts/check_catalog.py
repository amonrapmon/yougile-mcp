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


def _operation_test_cases() -> dict[str, dict]:
    source = (ROOT / "tests/test_api_client.py").read_text(encoding="utf-8")
    module = ast.parse(source)
    for node in module.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "OPERATION_CASES"
            for target in node.targets
        ):
            cases = ast.literal_eval(node.value)
            return cases if isinstance(cases, dict) else {}
    return {}


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


def _calls_bound_operation_case(
    test_method: ast.FunctionDef | ast.AsyncFunctionDef,
    operation_id_value: str,
) -> bool:
    operation_cases = _operation_test_cases()
    if operation_id_value not in operation_cases:
        return False
    for node in ast.walk(test_method):
        if not isinstance(node, (ast.For, ast.AsyncFor)):
            continue
        if not isinstance(node.target, (ast.Tuple, ast.List)) or len(node.target.elts) != 2:
            continue
        operation_id, case = node.target.elts
        if not (
            isinstance(operation_id, ast.Name)
            and operation_id.id == "operation_id"
            and isinstance(case, ast.Name)
            and case.id == "case"
        ):
            continue
        iterator = node.iter
        if not (
            isinstance(iterator, ast.Call)
            and isinstance(iterator.func, ast.Attribute)
            and iterator.func.attr == "items"
            and isinstance(iterator.func.value, ast.Name)
            and iterator.func.value.id == "OPERATION_CASES"
        ):
            continue
        valid_call = False
        invalid_call = False
        multipart_call = "multipart_file" not in operation_cases[operation_id_value]
        for child in ast.walk(node):
            if isinstance(child, ast.With):
                guarded = any(
                    isinstance(context.context_expr, ast.Call)
                    and isinstance(context.context_expr.func, ast.Attribute)
                    and context.context_expr.func.attr == "assertRaises"
                    and context.context_expr.args
                    and isinstance(context.context_expr.args[0], ast.Name)
                    and context.context_expr.args[0].id == "InvalidInputError"
                    for context in child.items
                )
                if guarded and any(
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Attribute)
                    and call.func.attr == "request"
                    and any(
                        keyword.arg is None
                        and isinstance(keyword.value, ast.Subscript)
                        and isinstance(keyword.value.value, ast.Name)
                        and keyword.value.value.id == "case"
                        and isinstance(keyword.value.slice, ast.Constant)
                        and keyword.value.slice.value == "invalid"
                        for keyword in call.keywords
                    )
                    and any(
                        keyword.arg == "operation_id"
                        and isinstance(keyword.value, ast.Name)
                        and keyword.value.id == "operation_id"
                        for keyword in call.keywords
                    )
                    for call in ast.walk(child)
                ):
                    invalid_call = True
            if not isinstance(child, ast.Call) or not isinstance(child.func, ast.Attribute):
                continue
            if child.func.attr != "request":
                continue
            keywords = {keyword.arg: keyword.value for keyword in child.keywords}
            if not (
                isinstance(keywords.get("operation_id"), ast.Name)
                and keywords["operation_id"].id == "operation_id"
            ):
                continue
            if all(
                isinstance(keywords.get(name), ast.Subscript)
                and isinstance(keywords[name].value, ast.Name)
                and keywords[name].value.id == "case"
                for name in ("path", "query")
            ) and isinstance(keywords.get("body"), ast.Call):
                valid_call = True
                multipart = keywords.get("multipart_file")
                if (
                    isinstance(multipart, ast.Call)
                    and isinstance(multipart.func, ast.Attribute)
                    and isinstance(multipart.func.value, ast.Name)
                    and multipart.func.value.id == "case"
                    and multipart.func.attr == "get"
                    and multipart.args
                    and isinstance(multipart.args[0], ast.Constant)
                    and multipart.args[0].value == "multipart_file"
                ):
                    multipart_call = True
        if valid_call and invalid_call and multipart_call:
            return True
    return False


def _test_binding_errors(operations: list[dict], test_methods: dict[str, ast.AST]) -> list[str]:
    errors = []
    operation_cases = _operation_test_cases()
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
            elif client_call == "request" and "operation_id" in kwargs:
                operation_id = kwargs["operation_id"]
                case = operation_cases.get(operation_id)
                if operation_id != item["operationId"]:
                    errors.append(f"Test binding operationId mismatch: {item['operationId']}")
                elif not isinstance(case, dict):
                    errors.append(f"Operation test case is missing: {operation_id}")
                elif (
                    case.get("method") != item["method"]
                    or case.get("path_template") != item["path"]
                    or not isinstance(case.get("expected_path"), str)
                    or not isinstance(case.get("invalid"), dict)
                    or item["effect"] != (
                        "read"
                        if item["method"] == "GET" or operation_id == "AuthKeyController_search"
                        else "destructive"
                        if item["method"] == "DELETE"
                        else "write"
                    )
                ):
                    errors.append(f"Operation test case differs from catalog: {operation_id}")
                elif not _calls_bound_operation_case(test_method, operation_id):
                    errors.append(
                        f"Test does not invoke the bound operation case: {operation_id}"
                    )
            elif not _calls_client_method(test_method, client_call, kwargs):
                errors.append(
                    f"Test does not call {client_call} for {item['operationId']}: {method_name}"
                )
    return errors


def _coverage_metadata_errors(operations: list[dict], source_sha256: str) -> list[str]:
    errors = []
    live_evidence = {"not_tested", "curl_observed", "live_verified_via_client"}
    for item in operations:
        operation_id = item.get("operationId", "<unknown>")
        evidence = item.get("live_evidence")
        if evidence not in live_evidence:
            errors.append(f"Unknown live evidence status: {operation_id}")
        if item.get("status") == "live_verified" and evidence != "live_verified_via_client":
            errors.append(f"live_verified operation lacks Python-client evidence: {operation_id}")
        overlay = item.get("compatibility_overlay")
        if overlay is not None and (
            not isinstance(overlay, dict)
            or not isinstance(overlay.get("version"), str)
            or overlay.get("source_sha256") != source_sha256
        ):
            errors.append(f"Compatibility overlay is not tied to the pinned source: {operation_id}")
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
    metadata_errors = _coverage_metadata_errors(operations, source.get("sha256", ""))
    if metadata_errors:
        raise SystemExit("\n".join(metadata_errors))
    if any(item["live_evidence"] == "curl_observed" for item in operations) and not (
        ROOT / "docs/verification/yougile-live-2026-11-14.md"
    ).is_file():
        raise SystemExit("curl-observed coverage must link to its sanitized evidence document")
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
