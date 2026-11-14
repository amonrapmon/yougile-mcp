#!/usr/bin/env python3
"""Run bounded, sanitized probes against a confirmed disposable YouGile company."""

# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from yougile_mcp.api.client import IMPLEMENTED_OPERATION_IDS, YouGileClient  # noqa: E402
from yougile_mcp.api.errors import ApiError  # noqa: E402
from yougile_mcp.api.spec import Operation, operations  # noqa: E402
from yougile_mcp.config import Settings  # noqa: E402

MAX_REQUESTS = 50
DEFAULT_REQUEST_LIMIT = 20
PREFLIGHT_OPERATION_IDS = ("UserController_getMe", "CompanyController_get")
_REFERENCE = re.compile(r"^\$([A-Za-z0-9_-]+)\.(.+)$")
_STEP_ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
_FIXTURE_PREFIX = re.compile(r"^YOUGILE_MCP_E2E_[A-Za-z0-9_-]{6,40}$")
_CREDENTIAL_OPERATIONS = {
    "getCompanies",
    "AuthKeyController_search",
    "AuthKeyController_create",
    "AuthKeyController_delete",
}
_SENSITIVE_OPERATIONS = {
    "AuthKeyController_create",
    "AuthKeyController_delete",
    "ChatMessageController_sendMessage",
    "ChatMessageController_typing",
    "ChatMessageController_update",
    "CompanyController_update",
    "CrmContactPersonsController_create",
    "CrmExternalIdController_findContactByExternalId",
    "FileController_uploadFile",
    "GroupChatController_create",
    "GroupChatController_update",
    "ProjectRolesController_create",
    "ProjectRolesController_delete",
    "ProjectRolesController_update",
    "TaskController_updateChatSubscribers",
    "UserController_create",
    "UserController_delete",
    "UserController_update",
    "UserController_setCustomStatus",
    "UserController_clearCustomStatus",
    "WebhookController_create",
    "WebhookController_put",
}
_SECRET_FIELD_MARKERS = ("apikey", "authorization", "password", "secret", "token")


class PlanError(ValueError):
    """A plan is invalid; its contents are never included in the message."""


def load_local_credentials(env_file: Path | None = None) -> bool:
    """Load only the two documented E2E settings from the user's profile file."""
    path = env_file or Path.home() / ".config" / "yougile-mcp" / "e2e.env"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False

    accepted = {"YOUGILE_API_KEY", "YOUGILE_COMPANY_ID"}
    for line in lines:
        item = line.strip()
        if not item or item.startswith("#") or "=" not in item:
            continue
        name, value = item.split("=", 1)
        name, value = name.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if name in accepted and value and not os.environ.get(name):
            os.environ[name] = value
    return all(os.environ.get(name) for name in accepted)


def load_plan(path: Path) -> dict[str, Any]:
    """Read a local plan without ever echoing its IDs, arguments or payloads."""
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise PlanError("plan_must_be_outside_repository")

    try:
        plan = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise PlanError("plan_unreadable") from None
    if not isinstance(plan, dict) or _contains_secret_field(plan):
        raise PlanError("plan_invalid")
    if set(plan) - {"company_scope", "fixture_ids", "fixture_prefix", "callback_urls", "steps"}:
        raise PlanError("plan_invalid")
    if plan.get("company_scope") != "disposable_test_company":
        raise PlanError("company_scope_required")
    fixture_ids = plan.get("fixture_ids", [])
    steps = plan.get("steps")
    prefix = plan.get("fixture_prefix")
    if (
        not isinstance(fixture_ids, list)
        or any(not isinstance(item, str) or not item for item in fixture_ids)
        or len(set(fixture_ids)) != len(fixture_ids)
        or not isinstance(prefix, str)
        or _FIXTURE_PREFIX.fullmatch(prefix) is None
        or not isinstance(steps, list)
    ):
        raise PlanError("plan_invalid")
    callback_urls = plan.get("callback_urls", [])
    if not isinstance(callback_urls, list) or any(
        not isinstance(item, str) or not item.startswith("https://") for item in callback_urls
    ):
        raise PlanError("plan_invalid")

    available = operations()
    seen_step_ids: set[str] = set()
    seen_operation_ids: set[str] = set()
    for step in steps:
        if not isinstance(step, dict) or set(step) - {
            "step_id", "operationId", "path", "query", "body", "multipart_file"
        }:
            raise PlanError("plan_invalid")
        step_id = step.get("step_id")
        operation_id = step.get("operationId")
        if (
            not isinstance(step_id, str)
            or _STEP_ID.fullmatch(step_id) is None
            or step_id in seen_step_ids
            or not isinstance(operation_id, str)
            or operation_id not in available
            or operation_id in seen_operation_ids
        ):
            raise PlanError("plan_invalid")
        for field in ("path", "query"):
            if field in step and not isinstance(step[field], dict):
                raise PlanError("plan_invalid")
        if "multipart_file" in step and not isinstance(step["multipart_file"], dict):
            raise PlanError("plan_invalid")
        seen_step_ids.add(step_id)
        seen_operation_ids.add(operation_id)
    return plan


def build_read_only_plan() -> dict[str, Any]:
    """Probe each safe read once and chain detail reads to bounded list results."""
    steps: list[dict[str, Any]] = []

    def add(
        step_id: str,
        operation_id: str,
        *,
        path: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> None:
        step: dict[str, Any] = {"step_id": step_id, "operationId": operation_id}
        if path is not None:
            step["path"] = path
        if query is not None:
            step["query"] = query
        steps.append(step)

    page = {"limit": 1, "offset": 0}
    add("projects", "ProjectController_search", query=page)
    add("project", "ProjectController_get", path={"id": "$projects.content.0.id"})
    add(
        "project_roles",
        "ProjectRolesController_search",
        path={"projectId": "$projects.content.0.id"},
        query=page,
    )
    add(
        "project_role",
        "ProjectRolesController_get",
        path={"projectId": "$projects.content.0.id", "id": "$project_roles.content.0.id"},
    )
    add("boards", "BoardController_search", query=page)
    add("board", "BoardController_get", path={"id": "$boards.content.0.id"})
    add("columns", "ColumnController_search", query=page)
    add("column", "ColumnController_get", path={"id": "$columns.content.0.id"})
    add("tasks", "TaskController_search", query=page)
    add("task", "TaskController_get", path={"id": "$tasks.content.0.id"})
    add("task_log", "TaskController_getLog", path={"id": "$tasks.content.0.id"}, query={"limit": 1})
    add("task_subscribers", "TaskController_getChatSubscribers", path={"id": "$tasks.content.0.id"})
    add("tasks_reversed", "TaskController_searchReversed", query=page)
    add("departments", "DepartmentController_search", query=page)
    add("department", "DepartmentController_get", path={"id": "$departments.content.0.id"})
    add("users", "UserController_search", query=page)
    add("user", "UserController_get", path={"id": "$users.content.0.id"})
    add("group_chats", "GroupChatController_search", query=page)
    add("group_chat", "GroupChatController_get", path={"id": "$group_chats.content.0.id"})
    add(
        "messages",
        "ChatMessageController_search",
        path={"chatId": "$group_chats.content.0.id"},
        query=page,
    )
    add(
        "message",
        "ChatMessageController_get",
        path={"chatId": "$group_chats.content.0.id", "id": "$messages.content.0.id"},
    )
    add("sprint_stickers", "SprintStickerController_search", query=page)
    add(
        "sprint_sticker",
        "SprintStickerController_getSticker",
        path={"id": "$sprint_stickers.content.0.id"},
    )
    add(
        "sprint_sticker_state",
        "SprintStickerStateController_get",
        path={
            "stickerId": "$sprint_stickers.content.0.id",
            "stickerStateId": "$sprint_sticker.states.0.id",
        },
    )
    add("string_stickers", "StringStickerController_search", query=page)
    add(
        "string_sticker",
        "StringStickerController_get",
        path={"id": "$string_stickers.content.0.id"},
    )
    add(
        "string_sticker_state",
        "StringStickerStateController_get",
        path={
            "stickerId": "$string_stickers.content.0.id",
            "stickerStateId": "$string_sticker.states.0.id",
        },
    )
    add("webhooks", "WebhookController_search")
    return {
        "company_scope": "disposable_test_company",
        "fixture_ids": [],
        "fixture_prefix": "YOUGILE_MCP_E2E_GEN229_READONLY",
        "steps": steps,
    }


def _contains_secret_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            any(marker in str(key).casefold().replace("-", "_") for marker in _SECRET_FIELD_MARKERS)
            or _contains_secret_field(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_secret_field(item) for item in value)
    return False


def _required_inputs(operation: Operation) -> tuple[list[str], list[str], bool]:
    path_names = re.findall(r"\{([^{}]+)\}", operation.path)
    query_names = [
        item["name"]
        for item in operation.parameters
        if item.get("in") == "query" and item.get("required")
    ]
    body_required = bool(operation.request_body and operation.request_body.get("required"))
    return path_names, query_names, body_required


def _base_row(operation: Operation) -> dict[str, Any]:
    path_names, query_names, body_required = _required_inputs(operation)
    row = {
        "operationId": operation.operation_id,
        "method": operation.method,
        "path": operation.path,
        "effect": operation.effect,
        "planned": False,
        "status": "NOT RUN",
        "category": "dry_run_only",
        "http_status": None,
        "inputs": {
            "path": path_names,
            "required_query": query_names,
            "required_body": body_required,
        },
        "schema": None,
    }
    if operation.operation_id not in IMPLEMENTED_OPERATION_IDS:
        row.update(status="SKIPPED", category="sdk_operation_unavailable")
    elif operation.operation_id in _CREDENTIAL_OPERATIONS and operation.effect == "read":
        row.update(status="SKIPPED", category="credential_bearing_operation")
    elif operation.effect == "destructive":
        row.update(status="BLOCKED", category="destructive_approval_required")
    elif operation.effect == "write":
        row.update(status="BLOCKED", category="write_approval_required")
    elif path_names or query_names or body_required:
        row.update(status="BLOCKED", category="test_fixture_required")
    return row


def build_report(request_limit: int = DEFAULT_REQUEST_LIMIT) -> dict[str, Any]:
    return {
        "report_version": 1,
        "evidence": "live_sdk",
        "request_limit": request_limit,
        "requests_used": 0,
        "company_scope_matches_configured_id": None,
        "operations": [_base_row(op) for op in sorted(operations().values(), key=lambda item: item.operation_id)],
    }


def build_plan_preview(plan: dict[str, Any], request_limit: int) -> dict[str, Any]:
    report = build_report(request_limit)
    available = operations()
    for step in plan["steps"]:
        row = _find_row(report, step["operationId"])
        row["planned"] = True
        operation = available[step["operationId"]]
        if operation.operation_id in _CREDENTIAL_OPERATIONS and operation.effect == "read":
            row.update(status="SKIPPED", category="credential_bearing_operation")
        elif operation.effect != "read":
            row.update(
                status="BLOCKED",
                category=(
                    "destructive_approval_required"
                    if operation.effect == "destructive"
                    else "write_approval_required"
                ),
            )
        else:
            row.update(status="NOT RUN", category="dry_run_no_network")
    return report


def _find_row(report: dict[str, Any], operation_id: str) -> dict[str, Any]:
    return next(row for row in report["operations"] if row["operationId"] == operation_id)


def _mark(report: dict[str, Any], operation_id: str, status: str, category: str) -> None:
    row = _find_row(report, operation_id)
    row.update(status=status, category=category, http_status=None, schema=None)


def _resolve(value: Any, outputs: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _resolve(item, outputs) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve(item, outputs) for item in value]
    if not isinstance(value, str) or not value.startswith("$"):
        return value
    match = _REFERENCE.fullmatch(value)
    if match is None:
        raise KeyError
    step_id, raw_path = match.groups()
    current: Any = outputs[step_id]
    for part in raw_path.split("."):
        if isinstance(current, list) and part.isdecimal():
            current = current[int(part)]
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise KeyError
    return current


def _strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _fixture_gate(
    operation: Operation,
    *,
    path: dict[str, Any],
    body: Any,
    multipart_file: dict[str, Any] | None,
    fixture_ids: set[str],
    created_ids: set[str],
    observed_ids: set[str],
    fixture_prefix: str,
    callback_urls: set[str],
    allow_writes: bool,
    allow_destructive: bool,
    allow_sensitive: bool,
) -> str | None:
    if operation.operation_id in _CREDENTIAL_OPERATIONS:
        return "credential_bearing_operation"
    if operation.operation_id not in IMPLEMENTED_OPERATION_IDS:
        return "sdk_operation_unavailable"
    if operation.effect == "destructive" and not allow_destructive:
        return "destructive_approval_required"
    if operation.effect == "write" and not allow_writes:
        return "write_approval_required"
    if operation.operation_id in _SENSITIVE_OPERATIONS and not allow_sensitive:
        return "sensitive_operation_approval_required"
    if operation.operation_id == "ChatMessageController_sendMessage" and not any(
        fixture_prefix in item for item in _strings(body)
    ):
        return "test_message_marker_required"
    if operation.operation_id in {"WebhookController_create", "WebhookController_put"}:
        if not callback_urls and operation.operation_id == "WebhookController_create":
            return "test_callback_allowlist_required"
        url_values = _named_values(body, "url")
        if any(not isinstance(item, str) or item not in callback_urls for item in url_values):
            return "callback_not_allowlisted"

    owned_ids = fixture_ids | created_ids
    path_names, _, _ = _required_inputs(operation)
    if operation.effect != "read" and any(str(path.get(name, "")) not in owned_ids for name in path_names):
        return "target_not_in_fixture_allowlist"
    if operation.effect == "read" and any(
        str(path.get(name, "")) not in owned_ids | observed_ids for name in path_names
    ):
        return "target_not_in_fixture_allowlist"
    if operation.operation_id == "TaskController_updateChatSubscribers":
        subscriber_ids = body.get("content", []) if isinstance(body, dict) else []
        if not isinstance(subscriber_ids, list) or any(str(item) not in owned_ids for item in subscriber_ids):
            return "subscriber_not_in_fixture_allowlist"
    if operation.operation_id in {"GroupChatController_create", "GroupChatController_update"}:
        if isinstance(body, dict):
            for field in ("users", "userRoleMap"):
                members = body.get(field, {})
                if not isinstance(members, dict) or any(str(item) not in owned_ids for item in members):
                    return "chat_member_not_in_fixture_allowlist"
    if operation.effect != "read" and not path_names:
        payload = body
        if multipart_file:
            payload = {"filename": multipart_file.get("filename"), "content": multipart_file.get("content")}
        if not any(fixture_prefix in item for item in _strings(payload)):
            return "test_fixture_marker_required"
    if operation.operation_id == "FileController_uploadFile":
        if (
            not isinstance(multipart_file, dict)
            or not isinstance(multipart_file.get("filename"), str)
            or not isinstance(multipart_file.get("content"), str)
            or len(multipart_file["content"].encode("utf-8")) > 262_144
            or multipart_file.get("content_type", "text/plain") != "text/plain"
            or fixture_prefix not in multipart_file["content"]
        ):
            return "synthetic_text_upload_required"
    return None


def _named_values(value: Any, name: str):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == name:
                yield item
            else:
                yield from _named_values(item, name)
    elif isinstance(value, list):
        for item in value:
            yield from _named_values(item, name)


def _safe_error(row: dict[str, Any], error: ApiError) -> None:
    row.update(status="FAIL", category=error.category, http_status=error.status_code)
    diagnostic = error.diagnostic
    if diagnostic is not None:
        row["schema"] = {
            "path": diagnostic.path,
            "rule": diagnostic.rule,
            "expected_type": diagnostic.expected_type,
            "actual_type": diagnostic.actual_type,
        }


async def execute_plan(
    plan: dict[str, Any],
    *,
    request_limit: int,
    confirm_disposable_company: bool,
    allow_writes: bool,
    allow_destructive: bool,
    allow_sensitive: bool,
) -> dict[str, Any]:
    report = build_report(request_limit)
    available = operations()
    steps = plan["steps"]
    operations_by_step = {step["step_id"]: available[step["operationId"]] for step in steps}
    for step in steps:
        _find_row(report, step["operationId"])["planned"] = True
    for operation_id in PREFLIGHT_OPERATION_IDS:
        _find_row(report, operation_id)["planned"] = True

    if not confirm_disposable_company:
        for step in steps:
            _mark(report, step["operationId"], "BLOCKED", "disposable_company_confirmation_required")
        return report

    if len(PREFLIGHT_OPERATION_IDS) + len(steps) > request_limit:
        for step in steps:
            _mark(report, step["operationId"], "BLOCKED", "request_budget_exceeded")
        return report

    load_local_credentials()
    try:
        settings = Settings.from_env()
    except ValueError:
        settings = None
    if settings is None or not settings.has_api_key or not settings.company_id:
        for step in steps:
            _mark(report, step["operationId"], "BLOCKED", "credentials_unavailable")
        return report

    async with YouGileClient(settings, timeout=10, max_requests=request_limit) as client:
        preflight_failed = False
        for operation_id in PREFLIGHT_OPERATION_IDS:
            row = _find_row(report, operation_id)
            try:
                response = await client.request(operation_id)
            except ApiError as error:
                _safe_error(row, error)
                preflight_failed = True
            else:
                row.update(status="PASS", category="preflight", http_status=response.status_code)
                if operation_id == "CompanyController_get":
                    data = response.data if isinstance(response.data, dict) else {}
                    matches = data.get("id") == settings.company_id
                    report["company_scope_matches_configured_id"] = bool(matches)
                    if not matches:
                        _mark(report, operation_id, "FAIL", "company_scope_mismatch")
                        preflight_failed = True
            report["requests_used"] = client.requests_sent
        if report["company_scope_matches_configured_id"] is not True:
            preflight_failed = True
        if preflight_failed:
            for step in steps:
                _mark(report, step["operationId"], "BLOCKED", "company_preflight_failed")
            return report

        fixture_ids = set(plan["fixture_ids"])
        created_ids: set[str] = set()
        observed_ids: set[str] = set()
        outputs: dict[str, Any] = {}
        halt_reason = None
        for step in steps:
            operation = operations_by_step[step["step_id"]]
            row = _find_row(report, operation.operation_id)
            if halt_reason:
                _mark(report, operation.operation_id, "BLOCKED", halt_reason)
                continue
            try:
                path = _resolve(step.get("path", {}), outputs)
                query = _resolve(step.get("query", {}), outputs)
                body = _resolve(step.get("body"), outputs)
                multipart = _resolve(step.get("multipart_file"), outputs)
                if multipart is not None:
                    multipart = dict(multipart)
                gate = _fixture_gate(
                    operation,
                    path=path,
                    body=body,
                    multipart_file=multipart,
                    fixture_ids=fixture_ids,
                    created_ids=created_ids,
                    observed_ids=observed_ids,
                    fixture_prefix=plan["fixture_prefix"],
                    callback_urls=set(plan.get("callback_urls", [])),
                    allow_writes=allow_writes,
                    allow_destructive=allow_destructive,
                    allow_sensitive=allow_sensitive,
                )
            except (IndexError, KeyError, TypeError, ValueError):
                _mark(report, operation.operation_id, "SKIPPED", "no_test_fixture_found")
                continue
            if gate:
                _mark(report, operation.operation_id, "BLOCKED", gate)
                continue
            if any(
                isinstance(value, int) and not isinstance(value, bool) and value > 25
                for key, value in query.items()
                if key == "limit"
            ):
                _mark(report, operation.operation_id, "BLOCKED", "page_limit_exceeded")
                continue

            try:
                response = await client.request(
                    operation.operation_id,
                    path=path,
                    query=query,
                    body=body,
                    multipart_file=(
                        multipart["filename"],
                        multipart["content"].encode("utf-8"),
                        multipart.get("content_type", "text/plain"),
                    ) if multipart is not None else None,
                )
            except ApiError as error:
                _safe_error(row, error)
                if error.category == "uncertain_write":
                    halt_reason = "stopped_after_uncertain_write"
                elif error.category == "request_budget_exhausted":
                    halt_reason = "request_budget_exhausted"
                    row.update(status="BLOCKED", category="request_budget_exhausted")
                report["requests_used"] = client.requests_sent
                continue
            row.update(status="PASS", category=None, http_status=response.status_code)
            outputs[step["step_id"]] = response.data
            if operation.effect == "read":
                observed_ids.update(_collect_ids(response.data))
            if isinstance(response.data, dict) and isinstance(response.data.get("id"), str):
                created_ids.add(response.data["id"])
            report["requests_used"] = client.requests_sent
        report["requests_used"] = client.requests_sent

    return report


def _collect_ids(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, str) and (key == "id" or key.endswith("Id")):
                yield item
            else:
                yield from _collect_ids(item)
    elif isinstance(value, list):
        for item in value:
            yield from _collect_ids(item)


def _print_report(report: dict[str, Any]) -> None:
    print(f"requests: {report['requests_used']}/{report['request_limit']}")
    if report["company_scope_matches_configured_id"] is not None:
        print(f"configured company matches authenticated company: {str(report['company_scope_matches_configured_id']).lower()}")
    print("operationId\tmethod\tpath\teffect\tplanned\tstatus\tdetail")
    for row in report["operations"]:
        detail = row["category"] or ""
        if row["http_status"] is not None:
            detail += (" " if detail else "") + f"HTTP {row['http_status']}"
        if row["schema"]:
            item = row["schema"]
            detail += f" {item['path']} {item['rule']} expected={item['expected_type']} actual={item['actual_type']}"
        print(f"{row['operationId']}\t{row['method']}\t{row['path']}\t{row['effect']}\t{str(row['planned']).lower()}\t{row['status']}\t{detail}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="explicit network-free plan preview (also the default)")
    parser.add_argument("--execute", action="store_true", help="run the external plan; default is a network-free dry-run")
    parser.add_argument("--dry-run-read-only", action="store_true", help="preview the complete built-in read-only dependency chain without network access")
    parser.add_argument("--execute-read-only", action="store_true", help="run the complete built-in read-only suite")
    parser.add_argument("--plan-file", type=Path, help="local JSON plan stored outside the repository")
    parser.add_argument("--max-requests", type=int, default=DEFAULT_REQUEST_LIMIT, help="worst-case HTTP request budget (1-50, including read retries)")
    parser.add_argument("--confirm-disposable-company", action="store_true", help="owner attests the key is restricted to this disposable test company")
    parser.add_argument("--allow-writes", action="store_true", help="owner approved the reviewed plan's non-destructive writes")
    parser.add_argument("--allow-destructive", action="store_true", help="owner approved exact destructive targets in fixture_ids")
    parser.add_argument("--allow-sensitive", action="store_true", help="owner separately approved sensitive effects in the reviewed plan")
    args = parser.parse_args(argv)
    if not 1 <= args.max_requests <= MAX_REQUESTS:
        parser.error("--max-requests must be between 1 and 50")
    if args.execute and args.dry_run:
        parser.error("--execute cannot be combined with --dry-run")
    if args.dry_run_read_only and (args.execute or args.execute_read_only or args.plan_file is not None):
        parser.error("--dry-run-read-only cannot be combined with execution or --plan-file")
    if args.execute_read_only and (args.execute or args.dry_run or args.plan_file is not None):
        parser.error("--execute-read-only cannot be combined with --execute, --dry-run or --plan-file")
    if args.plan_file is not None:
        try:
            plan = load_plan(args.plan_file)
        except PlanError as error:
            print(f"plan: {error}", file=sys.stderr)
            return 2
    else:
        plan = None
    if args.execute and plan is None:
        parser.error("--execute requires --plan-file")

    if not args.execute and not args.execute_read_only:
        if args.dry_run_read_only:
            report = build_plan_preview(build_read_only_plan(), args.max_requests)
        elif plan is not None:
            report = build_plan_preview(plan, args.max_requests)
        else:
            report = build_report(args.max_requests)
    else:
        if args.execute_read_only:
            plan = build_read_only_plan()
        report = asyncio.run(
            execute_plan(
                plan,
                request_limit=args.max_requests,
                confirm_disposable_company=args.confirm_disposable_company,
                allow_writes=args.allow_writes,
                allow_destructive=args.allow_destructive,
                allow_sensitive=args.allow_sensitive,
            )
        )
    _print_report(report)
    return 1 if any(row["status"] == "FAIL" for row in report["operations"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
