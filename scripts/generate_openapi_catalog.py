#!/usr/bin/env python3
"""Regenerate the coverage matrix from the pinned official OpenAPI document.

SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from yougile_mcp.api.spec import (
    COMPATIBILITY_OVERLAY_SOURCE_SHA256,
    COMPATIBILITY_OVERLAY_VERSION,
    operation_effect,
)

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "src/yougile_mcp/api/openapi-v2.json"
SOURCE_PATH = ROOT / "src/yougile_mcp/api/openapi-source.json"
OUTPUT_PATH = ROOT / "catalog/openapi-operations.json"
MOCK_TESTS = {
    "getCompanies": {
        "test": "test_company_lookup_keeps_credentials_in_body_without_bearer",
        "call": "get_companies",
    },
    "BoardController_search": {
        "test": "test_headers_query_and_response_dto",
        "call": "search_boards",
    },
    "BoardController_get": {
        "test": "test_board_detail_and_column_list_schemas",
        "call": "get_board",
    },
    "ColumnController_search": {
        "test": "test_board_detail_and_column_list_schemas",
        "call": "search_columns",
    },
    "ColumnController_create": {
        "test": "test_write_sends_json_body_and_returns_created_dto",
        "call": "create_column",
    },
    "TaskController_search": {
        "test": "test_task_search_maps_both_confirmed_list_operations",
        "call": "search_tasks",
        "kwargs": {"reversed_order": False},
    },
    "TaskController_searchReversed": {
        "test": "test_task_search_maps_both_confirmed_list_operations",
        "call": "search_tasks",
        "kwargs": {"reversed_order": True},
    },
    "TaskController_get": {
        "test": "test_path_value_is_percent_encoded",
        "call": "get_task",
    },
}
READ_OPERATION_IDS = {
    "AuthKeyController_search",
    "ChatMessageController_get",
    "ChatMessageController_search",
    "CompanyController_get",
    "CrmExternalIdController_findContactByExternalId",
    "DepartmentController_get",
    "DepartmentController_search",
    "ColumnController_get",
    "GroupChatController_get",
    "GroupChatController_search",
    "ProjectController_get",
    "ProjectController_search",
    "ProjectRolesController_get",
    "ProjectRolesController_search",
    "SprintStickerController_getSticker",
    "SprintStickerController_search",
    "SprintStickerStateController_get",
    "StringStickerController_get",
    "StringStickerController_search",
    "StringStickerStateController_get",
    "TaskController_getChatSubscribers",
    "TaskController_getLog",
    "UserController_get",
    "UserController_getMe",
    "UserController_search",
    "WebhookController_search",
}
WRITE_OPERATION_IDS = {
    "AuthKeyController_create",
    "BoardController_create",
    "BoardController_update",
    "CompanyController_update",
    "ChatMessageController_sendMessage",
    "ChatMessageController_typing",
    "ChatMessageController_update",
    "ColumnController_update",
    "CrmContactPersonsController_create",
    "DepartmentController_create",
    "DepartmentController_update",
    "GroupChatController_create",
    "GroupChatController_update",
    "ProjectController_create",
    "ProjectController_update",
    "ProjectRolesController_create",
    "ProjectRolesController_update",
    "SprintStickerController_create",
    "SprintStickerController_update",
    "SprintStickerStateController_create",
    "SprintStickerStateController_update",
    "StringStickerController_create",
    "StringStickerController_update",
    "StringStickerStateController_create",
    "StringStickerStateController_update",
    "TaskController_create",
    "TaskController_update",
    "TaskController_updateChatSubscribers",
    "UserController_create",
    "UserController_setCustomStatus",
    "UserController_update",
    "WebhookController_create",
    "WebhookController_put",
    "FileController_uploadFile",
}
DESTRUCTIVE_OPERATION_IDS = {
    "AuthKeyController_delete",
    "ProjectRolesController_delete",
    "UserController_clearCustomStatus",
    "UserController_delete",
}
MOCK_TESTS.update(
    {
        operation_id: {
            "test": "test_operation_contracts",
            "call": "request",
            "kwargs": {"operation_id": operation_id},
        }
        for operation_id in READ_OPERATION_IDS | WRITE_OPERATION_IDS | DESTRUCTIVE_OPERATION_IDS
    }
)
CURL_OBSERVED_OPERATION_IDS = {
    "CompanyController_get",
    "WebhookController_create",
    "WebhookController_put",
    "WebhookController_search",
    "FileController_uploadFile",
}
SDK_PASS_OPERATION_IDS = {
    "BoardController_get",
    "BoardController_search",
    "ChatMessageController_search",
    "ColumnController_get",
    "ColumnController_search",
    "CompanyController_get",
    "CompanyController_update",
    "DepartmentController_get",
    "DepartmentController_search",
    "FileController_uploadFile",
    "GroupChatController_get",
    "GroupChatController_search",
    "BoardController_create",
    "BoardController_update",
    "ColumnController_create",
    "ColumnController_update",
    "DepartmentController_create",
    "DepartmentController_update",
    "ProjectController_create",
    "ProjectController_update",
    "ProjectRolesController_create",
    "ProjectRolesController_delete",
    "ProjectRolesController_get",
    "ProjectRolesController_update",
    "SprintStickerController_create",
    "SprintStickerController_getSticker",
    "SprintStickerController_update",
    "SprintStickerStateController_create",
    "SprintStickerStateController_get",
    "SprintStickerStateController_update",
    "StringStickerController_create",
    "StringStickerController_get",
    "StringStickerController_update",
    "StringStickerStateController_create",
    "StringStickerStateController_get",
    "StringStickerStateController_update",
    "TaskController_create",
    "TaskController_update",
    "WebhookController_create",
    "WebhookController_put",
    "ProjectController_search",
    "ProjectRolesController_search",
    "SprintStickerController_search",
    "StringStickerController_search",
    "TaskController_getChatSubscribers",
    "TaskController_getLog",
    "TaskController_search",
    "TaskController_searchReversed",
    "ProjectController_get",
    "UserController_get",
    "UserController_getMe",
    "UserController_search",
    "WebhookController_search",
    "TaskController_get",
}
SDK_MISMATCH_OPERATION_IDS: set[str] = set()
SDK_EXPECTED_ERROR_OPERATION_IDS = {"CrmExternalIdController_findContactByExternalId"}
SDK_VALIDATION_ERROR_OPERATION_IDS = {
    "CrmContactPersonsController_create",
    "UserController_create",
}
COMPATIBILITY_OVERLAY_OPERATION_IDS = {
    "BoardController_get",
    "BoardController_search",
    "TaskController_search",
    "CompanyController_get",
    "CompanyController_update",
    "CrmExternalIdController_findContactByExternalId",
    "GroupChatController_search",
    "GroupChatController_get",
    "ProjectController_get",
    "ProjectController_search",
    "ProjectRolesController_delete",
    "TaskController_get",
    "WebhookController_create",
    "WebhookController_put",
    "WebhookController_search",
    "FileController_uploadFile",
}
COMPATIBILITY_NOTES = {
    "BoardController_get": (
        "GEN-229 first live SDK GET returned deleted=null; the narrow BoardDto "
        "overlay was followed by a successful SDK GET. Invalid types remain rejected."
    ),
    "BoardController_search": (
        "GEN-229 repeated the live SDK GET successfully after the list DTO overlay "
        "for deleted=null; invalid non-boolean values remain rejected."
    ),
    "ProjectController_search": (
        "GEN-229 repeated the live SDK GET successfully after the list DTO overlay "
        "for deleted=null; invalid non-boolean values remain rejected."
    ),
    "TaskController_search": (
        "GEN-229 repeated the live SDK GET successfully after the list DTO overlay "
        "for deleted=null; invalid non-boolean values remain rejected."
    ),
    "CompanyController_get": (
        "The no-ID current-company route and deleted=null compatibility were "
        "confirmed by both owner-supplied curl evidence and GEN-229 SDK GET."
    ),
    "CompanyController_update": (
        "Live no-op PUT on the authenticated test company returned HTTP 200; "
        "the original title remained unchanged."
    ),
    "CrmContactPersonsController_create": (
        "A diagnostic create using a non-CRM project was rejected with HTTP 400. "
        "The operation remains blocked because the test company has no valid CRM "
        "project fixture; valid-payload behavior is unverified."
    ),
    "CrmExternalIdController_findContactByExternalId": (
        "A live lookup for a synthetic absent external ID returned HTTP 404; "
        "the overlay records this response while the pinned snapshot lists only 200. "
        "A positive lookup still needs a CRM external-ID fixture."
    ),
    "WebhookController_create": (
        "Overlay keeps filter name as a string and accepts string or string-array "
        "values per the pinned OAS examples; curl confirmed only the title/string "
        "filter and HTTP 201 response."
    ),
    "WebhookController_put": (
        "Overlay keeps filter name as a string and accepts string or string-array "
        "values per the pinned OAS examples; curl confirmed disabled=true persisted "
        "after PUT, not the location-array filter."
    ),
    "WebhookController_search": (
        "Overlay decodes the curl-observed response as an array and accepts string "
        "or string-array filter values per the pinned OAS examples; curl confirmed "
        "only the title/string filter, not location arrays."
    ),
    "FileController_uploadFile": (
        "Overlay removes the malformed multipart ref and accepts the curl-observed "
        "201 FileUploadDto; size and MIME limits are configurable client policy."
    ),
    "GroupChatController_search": (
        "GEN-229 first live SDK GET returned deleted=null in list items; the "
        "narrow GroupChatListDtoBase overlay was followed by a successful SDK GET."
    ),
    "GroupChatController_get": (
        "GEN-229 follow-up SDK GET found deleted=null after the group-chat list "
        "overlay; the narrow GroupChatDto overlay was followed by a successful GET. "
        "Invalid values remain rejected."
    ),
    "ProjectController_get": (
        "GEN-229 first live SDK GET returned deleted=null; the narrow ProjectDto "
        "overlay was followed by a successful SDK GET. Invalid types remain rejected."
    ),
    "ProjectRolesController_delete": (
        "GEN-229 live DELETE returned ProjectRoleDto with only id; the operation-only "
        "overlay requires id and validates any other present fields."
    ),
    "TaskController_get": (
        "GEN-229 first live SDK GET returned deleted=null; the narrow TaskDto "
        "overlay was followed by a successful SDK GET. Invalid types remain rejected."
    ),
    "UserController_create": (
        "Two synthetic test-user creates were rejected with HTTP 400; the SDK "
        "sanitizes the response body, so the server validation reason is unknown. "
        "Dependent user and chat writes were not attempted."
    ),
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
                    "effect": operation_effect(operation_id, method),
                    "status": "mock_tested" if operation_id in MOCK_TESTS else "discovered",
                    "live_evidence": _live_evidence(operation_id),
                    "compatibility_overlay": {
                        "version": COMPATIBILITY_OVERLAY_VERSION,
                        "source_sha256": COMPATIBILITY_OVERLAY_SOURCE_SHA256,
                    }
                    if operation_id in COMPATIBILITY_OVERLAY_OPERATION_IDS
                    else None,
                    "test_bindings": [
                        {
                            "test_path": (
                                "tests/test_api_client.py::ApiClientTests."
                                f"{MOCK_TESTS[operation_id]['test']}"
                            ),
                            "client_call": MOCK_TESTS[operation_id]["call"],
                            "kwargs": MOCK_TESTS[operation_id].get("kwargs", {}),
                        }
                    ]
                    if operation_id in MOCK_TESTS
                    else [],
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
    if operation_id in COMPATIBILITY_NOTES:
        return COMPATIBILITY_NOTES[operation_id]
    if operation_id in MOCK_TESTS:
        return None
    if operation_id in {"CompanyController_get", "CompanyController_update"}:
        return "The vendor path contains a non-standard wildcard with no declared parameter schema."
    if operation_id.startswith("WebhookController_"):
        return (
            "The pinned OAS declares WebhookFilters.name.items as unsupported type "
            "'location', conflicting with its string-name example; needs vendor clarification."
        )
    if operation_id == "FileController_uploadFile":
        return (
            "The multipart requestBody points to the empty schema reference "
            "'#/components/schemas/'; upload limits and allowed MIME types "
            "need an approved client policy."
        )
    return "Not yet covered by a MockTransport contract."


def _live_evidence(operation_id: str) -> str:
    if operation_id in SDK_MISMATCH_OPERATION_IDS:
        return "live_mismatch_via_client"
    if operation_id in SDK_EXPECTED_ERROR_OPERATION_IDS:
        return "live_expected_error_via_client"
    if operation_id in SDK_VALIDATION_ERROR_OPERATION_IDS:
        return "live_validation_error_via_client"
    if operation_id in SDK_PASS_OPERATION_IDS:
        return "live_verified_via_client"
    if operation_id in CURL_OBSERVED_OPERATION_IDS:
        return "curl_observed"
    return "not_tested"


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
