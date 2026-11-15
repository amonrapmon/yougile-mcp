"""GEN-231 Universal Tool Factory and 72/72 dispatcher MockTransport contracts."""

from __future__ import annotations

import base64
import json
import unittest
from typing import Any

import httpx
from jsonschema import Draft202012Validator

from test_api_client import OPERATION_CASES, _sample_schema
from yougile_mcp.api import YouGileClient
from yougile_mcp.api.spec import load_compatible_spec, operations
from yougile_mcp.config import Settings
from yougile_mcp.mcp.dispatch import (
    InvocationPrincipal,
    OneTimeApprovals,
    ToolDispatcher,
    ToolDispatchError,
)
from yougile_mcp.mcp.factory import build_registry

COMPANY = "isolated-test-company"
PROJECT = "owned-test-project"
SECRET = "synthetic-mock-key"


def _principal(*, company: str = COMPANY, scopes: frozenset[str] | None = None,
               projects: frozenset[str] | None = None, wide: bool = True) -> InvocationPrincipal:
    registry = build_registry()
    return InvocationPrincipal(
        subject="synthetic-agent", company_id=company,
        scopes=scopes if scopes is not None else frozenset(
            {d.scope for d in registry.list()}
            | {"yougile." + d.domain + ".destructive" for d in registry.list()}
        ),
        allowed_projects=projects if projects is not None else frozenset({PROJECT}),
        company_wide=wide,
    )


async def _project(principal: InvocationPrincipal, descriptor: Any, arguments: Any) -> str:
    # Mock source of truth: in production this must verify the underlying
    # resource's actual project and company from trusted server-side data.
    return PROJECT


async def _secrets(principal: InvocationPrincipal, operation_id: str) -> dict[str, Any]:
    if operation_id == "AuthKeyController_delete":
        return {"path": {"key": "synthetic-auth-key"}}
    if operation_id == "getCompanies":
        return {"body": {"login": "mock@example.test", "password": SECRET}}
    return {"body": {
        "login": "mock@example.test", "password": SECRET, "companyId": COMPANY,
    }}


def _sample_result(operation_id: str) -> tuple[int, Any]:
    op = operations()[operation_id]
    success = sorted(
        int(status) for status in op.responses if status.isdigit()
        and 200 <= int(status) < 300
    )
    status = success[0]
    content = op.responses[str(status)].get("content", {})
    media = content.get("application/json") or content.get("text/plain")
    body = (_sample_schema(media["schema"], load_compatible_spec())
            if media is not None else None)
    return status, body


def _arguments(operation_id: str) -> dict[str, Any]:
    descriptor = build_registry().by_operation(operation_id)
    case = OPERATION_CASES.get(operation_id, {})
    op = operations()[operation_id]
    args: dict[str, Any] = {}
    if "path" in descriptor.input_schema["properties"]:
        args["path"] = case.get("path") or {
            param["name"]: "synthetic-id"
            for param in op.parameters if param.get("in") == "path"
        }
    if "query" in descriptor.input_schema["properties"]:
        args["query"] = case.get("query", {})
    if "body" in descriptor.input_schema["properties"]:
        if "body" in case:
            args["body"] = case["body"]
        else:
            media = op.request_body["content"]["application/json"]
            args["body"] = _sample_schema(media["schema"], load_compatible_spec())
    if descriptor.multipart:
        args["multipart_file"] = {
            "filename": "synthetic.txt",
            "content_base64": base64.b64encode(b"mock upload").decode("ascii"),
            "content_type": "text/plain",
        }
    return args


def _response(operation_id: str) -> tuple[int, Any]:
    case = OPERATION_CASES.get(operation_id, {})
    if "response_body" in case or case.get("empty_response"):
        return case.get("status_code", 200), case.get("response_body")
    if case.get("status_code") is not None:
        code = case["status_code"]
        op = operations()[operation_id]
        media = op.responses[str(code)].get("content", {}).get("application/json")
        return code, _sample_schema(media["schema"], load_compatible_spec()) if media else None
    return _sample_result(operation_id)


class FactoryTests(unittest.TestCase):
    def test_registry_and_policy_cover_exactly_all_72(self):
        registry = build_registry()
        self.assertEqual(len(registry), 72)
        self.assertEqual({d.operation_id for d in registry.list()}, set(operations()))
        self.assertEqual(len({d.name for d in registry.list()}), 72)
        self.assertEqual(len({d.scope for d in registry.list()}) > 0, True)
        for descriptor in registry.list():
            with self.subTest(operation=descriptor.operation_id):
                self.assertEqual(registry.get(descriptor.name), descriptor)
                self.assertEqual(registry.by_operation(descriptor.operation_id), descriptor)
                self.assertTrue(descriptor.description)
                self.assertTrue(descriptor.scope.startswith("yougile."))
                self.assertIn(descriptor.access, {"read", "write", "destructive", "admin"})
                self.assertIn(descriptor.resource_scope, {"project", "company"})
                Draft202012Validator.check_schema(descriptor.input_schema)
                Draft202012Validator.check_schema(descriptor.output_schema)
                self.assertEqual(descriptor.method, operations()[descriptor.operation_id].method)
                self.assertTrue(descriptor.errors)
                if descriptor.access in {"admin", "destructive"}:
                    self.assertTrue(descriptor.requires_approval)
                if descriptor.credentials:
                    self.assertNotIn("body", descriptor.input_schema["properties"])

    def test_nullable_and_references_are_preserved(self):
        board = build_registry().by_operation("BoardController_get")
        self.assertIn("$defs", board.output_schema)
        self.assertIn("BoardDto", board.output_schema["$defs"])
        deleted = board.output_schema["$defs"]["BoardDto"]["properties"]["deleted"]
        self.assertIn("null", deleted["type"])
        self.assertNotIn("nullable", json.dumps(board.output_schema))


class DispatcherTests(unittest.IsolatedAsyncioTestCase):
    async def _run_case(self, operation_id: str) -> None:
        registry = build_registry()
        descriptor = registry.by_operation(operation_id)
        args = _arguments(operation_id)
        code, response_body = _response(operation_id)
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if response_body is None:
                return httpx.Response(code)
            return httpx.Response(code, json=response_body)

        events: list[dict[str, str]] = []
        settings = Settings.from_env({
            "YOUGILE_API_KEY": SECRET, "YOUGILE_COMPANY_ID": COMPANY,
        })
        async with YouGileClient(
            settings, transport=httpx.MockTransport(handler),
        ) as client:
            approvals = OneTimeApprovals()
            dispatcher = ToolDispatcher(
                client, company_id=COMPANY, registry=registry,
                project_resolver=_project, secret_resolver=_secrets,
                approvals=approvals, audit=lambda entry: events.append(dict(entry)),
            )
            with self.assertRaises(ToolDispatchError) as denied:
                await dispatcher.call(descriptor.name, args, _principal(scopes=frozenset()))
            self.assertEqual(denied.exception.category, "permission_denied")
            self.assertEqual(requests, [])

            with self.assertRaises(ToolDispatchError) as invalid:
                await dispatcher.call(descriptor.name, {"not_a_valid_parameter": True}, _principal())
            self.assertEqual(invalid.exception.category, "invalid_input")
            self.assertEqual(requests, [])

            elevated = isinstance(args.get("body"), dict) and "deleted" in args["body"]
            if descriptor.requires_approval or elevated:
                approvals.grant(_principal(), descriptor, args)
            response = await dispatcher.call(descriptor.name, args, _principal())
            self.assertEqual(response["status_code"], code)
            expected_data = {"redacted": True} if descriptor.redacted_result else response_body
            self.assertEqual(response["data"], expected_data)
            self.assertEqual(len(requests), 1)
            self.assertEqual(requests[0].method, descriptor.method)
            self.assertEqual(events[-1]["outcome"], "success")

    async def test_all_72_operations_through_dispatcher_and_real_api_client(self):
        coverage: list[str] = []
        for descriptor in build_registry().list():
            with self.subTest(operation=descriptor.operation_id):
                await self._run_case(descriptor.operation_id)
                coverage.append(descriptor.operation_id)
        self.assertEqual(len(coverage), 72)
        self.assertEqual(set(coverage), set(operations()))

    async def test_cross_company_and_project_denied_before_http(self):
        calls = []
        async def wrong_project(*_: Any) -> str:
            return "other-project"
        settings = Settings.from_env({
            "YOUGILE_API_KEY": SECRET, "YOUGILE_COMPANY_ID": COMPANY,
        })
        async with YouGileClient(
            settings, transport=httpx.MockTransport(lambda request: calls.append(request)),
        ) as client:
            dispatcher = ToolDispatcher(
                client, company_id=COMPANY, project_resolver=wrong_project,
            )
            tool = build_registry().by_operation("BoardController_get")
            args = {"path": {"id": "board-id"}}
            for principal in (None, _principal(company="other-company"), _principal(wide=False)):
                with self.assertRaises(ToolDispatchError):
                    await dispatcher.call(tool.name, args, principal)
            self.assertEqual(calls, [])

    async def test_approval_is_one_shot_payload_bound(self):
        settings = Settings.from_env({
            "YOUGILE_API_KEY": SECRET, "YOUGILE_COMPANY_ID": COMPANY,
        })
        registry = build_registry()
        tool = registry.by_operation("CompanyController_update")
        args = {"body": {"title": "synthetic company"}}
        approvals = OneTimeApprovals()
        approvals.grant(_principal(), tool, args)
        sent = []
        async with YouGileClient(
            settings, transport=httpx.MockTransport(
                lambda request: (sent.append(request) or httpx.Response(200, json={"id": "test-id"}))
            ),
        ) as client:
            dispatcher = ToolDispatcher(
                client, company_id=COMPANY, registry=registry, approvals=approvals,
            )
            with self.assertRaises(ToolDispatchError) as altered:
                await dispatcher.call(tool.name, {"body": {"title": "other"}}, _principal())
            self.assertEqual(altered.exception.category, "approval_required")
            await dispatcher.call(tool.name, args, _principal())
            with self.assertRaises(ToolDispatchError) as replay:
                await dispatcher.call(tool.name, args, _principal())
            self.assertEqual(replay.exception.category, "approval_required")
            self.assertEqual(len(sent), 1)

    async def test_vendor_failure_sanitized_and_denied_no_traffic(self):
        settings = Settings.from_env({
            "YOUGILE_API_KEY": SECRET, "YOUGILE_COMPANY_ID": COMPANY,
        })
        sent = []
        async with YouGileClient(
            settings, transport=httpx.MockTransport(
                lambda request: (sent.append(request) or httpx.Response(400, json={
                    "message": "private synthetic test token " + SECRET,
                }))
            ),
        ) as client:
            approvals = OneTimeApprovals()
            dispatcher = ToolDispatcher(client, company_id=COMPANY, approvals=approvals)
            tool = build_registry().by_operation("CompanyController_get")
            approvals.grant(_principal(), tool, {})
            with self.assertRaises(ToolDispatchError) as exc:
                await dispatcher.call(tool.name, {}, _principal())
            self.assertEqual(exc.exception.category, "vendor_validation")
            self.assertNotIn(SECRET, str(exc.exception))
            self.assertEqual(len(sent), 1)


if __name__ == "__main__":
    unittest.main()
