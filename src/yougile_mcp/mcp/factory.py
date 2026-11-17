"""Universal OpenAPI-driven MCP tool descriptor factory.

72 operations register from one client contract and reviewed per-operation policy.
SPDX-License-Identifier: AGPL-3.0-only
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any

from ..api.client import IMPLEMENTED_OPERATION_IDS
from ..api.spec import Operation, load_compatible_spec, operations
from .schema import assemble_schema

_ERROR_CATEGORIES = (
    "invalid_input", "permission_denied", "authentication_failed", "not_found",
    "rate_limited", "request_budget_exhausted", "timeout", "uncertain_write",
    "vendor_validation", "upstream_failure", "result_too_large",
    "approval_required", "credentials_unavailable",
)
_CREDENTIAL_OPS = frozenset({
    "getCompanies", "AuthKeyController_create", "AuthKeyController_search",
    "AuthKeyController_delete",
})
_SECRET_RESPONSE_OPS = frozenset({
    "AuthKeyController_create", "AuthKeyController_search", "getCompanies",
})
_UPLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "filename": {"type": "string", "minLength": 1, "maxLength": 255},
        "content_base64": {"type": "string", "minLength": 1, "maxLength": 2800000},
        "content_type": {"type": "string", "enum": ["text/plain"]},
    },
    "required": ["filename", "content_base64", "content_type"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class ToolDescriptor:
    name: str
    operation_id: str
    description: str
    method: str
    path: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    domain: str
    access: str
    risk: str
    scope: str
    resource_scope: str
    requires_approval: bool
    credentials: bool
    multipart: bool
    redacted_result: bool
    pagination: str | None
    safe_direct_body_fields: frozenset[str] = frozenset()
    errors: tuple[str, ...] = _ERROR_CATEGORIES

    @property
    def annotations(self) -> dict[str, bool]:
        return {
            "readOnlyHint": self.access == "read",
            "destructiveHint": self.access == "destructive" or self.requires_approval,
            "idempotentHint": self.method == "GET",
            "openWorldHint": True,
        }


class ToolRegistry:
    def __init__(self, descriptors: list[ToolDescriptor]):
        by_name = {item.name: item for item in descriptors}
        by_operation = {item.operation_id: item for item in descriptors}
        if len(by_name) != len(descriptors) or len(by_operation) != len(descriptors):
            raise ValueError("Duplicate MCP tool name or operationId")
        self._by_name = by_name
        self._by_operation = by_operation

    def __len__(self) -> int:
        return len(self._by_name)

    def list(self) -> tuple[ToolDescriptor, ...]:
        return tuple(self._by_name.values())

    def get(self, name: str) -> ToolDescriptor:
        return self._by_name[name]

    def by_operation(self, operation_id: str) -> ToolDescriptor:
        return self._by_operation[operation_id]


def _tool_name(operation_id: str) -> str:
    segments = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", operation_id)
    segments = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", segments)
    return "yg_v2_" + segments.lower()


def _parameter_schema(operation: Operation, location: str) -> dict[str, Any] | None:
    parameters = [x for x in operation.parameters if x.get("in") == location]
    if not parameters:
        return None
    return {
        "type": "object",
        "properties": {x["name"]: x["schema"] for x in parameters},
        "required": [x["name"] for x in parameters if x.get("required")],
        "additionalProperties": False,
    }


def _input_schema(operation: Operation, *, credentials: bool, multipart: bool) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    for location in ("path", "query"):
        part = _parameter_schema(operation, location)
        if part is None:
            continue
        if credentials and operation.operation_id == "AuthKeyController_delete":
            part["properties"].pop("key", None)
            part["required"] = [x for x in part["required"] if x != "key"]
            if not part["properties"]:
                continue
        properties[location] = part
        if part["required"]:
            required.append(location)
    if multipart:
        properties["multipart_file"] = _UPLOAD_SCHEMA
        required.append("multipart_file")
    elif operation.request_body and not credentials:
        content = operation.request_body.get("content", {})
        if "application/json" not in content:
            raise ValueError("Unsupported body type: " + operation.operation_id)
        properties["body"] = content["application/json"]["schema"]
        if operation.request_body.get("required"):
            required.append("body")
    return {
        "type": "object", "properties": properties,
        "required": required, "additionalProperties": False,
    }


def _output_schema(operation: Operation, *, redacted: bool) -> dict[str, Any]:
    if redacted:
        data_schemas: list[dict[str, Any]] = [{
            "type": "object",
            "properties": {"redacted": {"const": True}},
            "required": ["redacted"],
            "additionalProperties": False,
        }]
    else:
        data_schemas = []
        for code, response in operation.responses.items():
            if not code.isdigit() or not 200 <= int(code) < 300:
                continue
            content = response.get("content", {})
            if "application/json" in content:
                data_schemas.append(content["application/json"]["schema"])
            elif "text/plain" in content:
                data_schemas.append(content["text/plain"]["schema"])
            else:
                data_schemas.append({"type": "null"})
    statuses = [int(code) for code in operation.responses if code.isdigit() and 200 <= int(code) < 300]
    if not statuses:
        raise ValueError("No success response schema: " + operation.operation_id)
    unique = list({json.dumps(item, sort_keys=True): item for item in data_schemas}.values())
    data_schema = unique[0] if len(unique) == 1 else {"anyOf": unique}
    return {
        "type": "object",
        "properties": {
            "status_code": {"type": "integer", "enum": sorted(statuses)},
            "data": data_schema,
        },
        "required": ["status_code", "data"],
        "additionalProperties": False,
    }


@lru_cache(maxsize=1)
def build_registry() -> ToolRegistry:
    raw = json.loads(files(__package__).joinpath("policy-manifest.json").read_text(encoding="utf-8"))
    policies = raw["operations"]
    available = operations()
    if set(policies) != set(available) or set(available) != IMPLEMENTED_OPERATION_IDS:
        raise ValueError("Catalog, API client and policy manifest differ")
    spec = load_compatible_spec()
    definitions = spec["components"]["schemas"]
    descriptors = []
    for operation_id in sorted(available):
        operation = available[operation_id]
        policy = policies[operation_id]
        required_fields = {"domain", "access", "risk", "resource_scope", "approval"}
        optional_fields = {"safe_direct_body_fields"}
        if not required_fields.issubset(policy) or set(policy) - (required_fields | optional_fields):
            raise ValueError("Incomplete or unexpected policy for " + operation_id)
        if policy["access"] not in {"read", "write", "destructive", "admin"}:
            raise ValueError("Invalid access policy for " + operation_id)
        if policy["resource_scope"] not in {"company", "project"}:
            raise ValueError("Invalid resource boundary for " + operation_id)
        if policy["access"] in {"destructive", "admin"} and not policy["approval"]:
            raise ValueError("Unsafe policy for " + operation_id)
        safe_fields = policy.get("safe_direct_body_fields", [])
        # Reviewed, field-level exception to the normal administrative approval.
        # Do not let a manifest edit silently exempt another privileged action.
        if safe_fields and not (
            operation_id == "ProjectController_create"
            and safe_fields == ["title", "idempotencyKey"]
            and policy["access"] == "admin"
            and policy["resource_scope"] == "company"
            and policy["approval"] is True
        ):
            raise ValueError("Unreviewed safe direct policy for " + operation_id)
        credentials = operation_id in _CREDENTIAL_OPS
        multipart = operation_id == "FileController_uploadFile"
        redacted = operation_id in _SECRET_RESPONSE_OPS
        descriptors.append(ToolDescriptor(
            name=_tool_name(operation_id),
            operation_id=operation_id,
            description=(
                "YouGile REST v2: " + operation_id + " (" +
                operation.method + " " + operation.path + ")" +
                (
                    ". Projects without members may not appear in the UI. "
                    "For a visible project, first call UserController_getMe, then "
                    "set users to exactly {yourVerifiedUserId: 'admin'}; "
                    "other users/roles require server approval."
                    if operation_id == "ProjectController_create" else
                    ". For a project with no members or departments, the "
                    "authenticated company admin may add only their own verified "
                    "UserController_getMe ID as admin without server approval."
                    if operation_id == "ProjectController_update" else ""
                )
            ),
            method=operation.method, path=operation.path,
            input_schema=assemble_schema(
                _input_schema(operation, credentials=credentials, multipart=multipart),
                definitions,
            ),
            output_schema=assemble_schema(
                _output_schema(operation, redacted=redacted),
                definitions,
            ),
            domain=policy["domain"], access=policy["access"], risk=policy["risk"],
            scope="yougile." + policy["domain"] + "." + policy["access"],
            resource_scope=policy["resource_scope"],
            requires_approval=policy["approval"],
            safe_direct_body_fields=frozenset(safe_fields), credentials=credentials,
            multipart=multipart, redacted_result=redacted,
            pagination=(
                "cursor" if {"limit", "before"}.issubset(
                    {x["name"] for x in operation.parameters if x.get("in") == "query"}
                ) else "offset" if {"limit", "offset"}.issubset(
                    {x["name"] for x in operation.parameters if x.get("in") == "query"}
                ) else None
            ),
        ))
    return ToolRegistry(descriptors)
