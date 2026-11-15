"""Official MCP SDK v2 in-memory integration: 72 tools through the actual client."""

from __future__ import annotations

import json
import unittest
from typing import Any

import httpx
from mcp import Client

from test_mcp_factory import (
    COMPANY,
    SECRET,
    _arguments,
    _principal,
    _project,
    _response,
    _secrets,
)
from yougile_mcp.api import YouGileClient
from yougile_mcp.config import Settings
from yougile_mcp.mcp.dispatch import OneTimeApprovals, ToolDispatcher
from yougile_mcp.mcp.factory import build_registry
from yougile_mcp.mcp.runtime import make_mcp_server


class _NoWaitLimiter:
    async def acquire(self) -> None:
        # Transport is a memory mock, not the real YouGile budget.
        return None


class OfficialMCPIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_72_wire_contracts_with_client(self) -> None:
        registry = build_registry()
        sent: list[httpx.Request] = []
        # Resolve the canonical encoded HTTP route. httpx URL.path is decoded,
        # so a valid ID containing '/' would otherwise break template matching.
        def handler(request: httpx.Request) -> httpx.Response:
            sent.append(request)
            encoded_path = request.url.raw_path.split(b"?", 1)[0].decode("ascii")
            matches = [
                desc for desc in registry.list()
                if desc.method == request.method
                and _route_matches(desc.path, encoded_path)
            ]
            # /users/me must beat /users/{id}; static paths are more specific.
            matches.sort(key=lambda desc: desc.path.count("{"))
            op = matches[0].operation_id
            code, payload = _response(op)
            return httpx.Response(code, json=payload) if payload is not None else httpx.Response(code)

        cfg = Settings.from_env({"YOUGILE_API_KEY": SECRET, "YOUGILE_COMPANY_ID": COMPANY})
        async with YouGileClient(
            cfg, transport=httpx.MockTransport(handler), limiter=_NoWaitLimiter()
        ) as api:
            approvals = OneTimeApprovals()
            dispatcher = ToolDispatcher(
                api, company_id=COMPANY, registry=registry, project_resolver=_project,
                secret_resolver=_secrets, approvals=approvals,
            )
            async def resolve_principal(_: Any):
                return _principal()
            server = make_mcp_server(dispatcher, resolve_principal=resolve_principal)
            async with Client(server, raise_exceptions=True) as mcp_client:
                tools = await mcp_client.list_tools()
                # SDK v2 may return a parsed ListToolsResult or a list of Tool.
                listed = tools.tools if hasattr(tools, "tools") else tools
                self.assertEqual(len(listed), 72)
                self.assertEqual({tool.name for tool in listed}, {d.name for d in registry.list()})
                called: list[str] = []
                for desc in registry.list():
                    with self.subTest(operation=desc.operation_id):
                        args = _arguments(desc.operation_id)
                        elevated = isinstance(args.get("body"), dict) and "deleted" in args["body"]
                        if desc.requires_approval or elevated:
                            approvals.grant(_principal(), desc, args)
                        response = await mcp_client.call_tool(desc.name, args)
                        self.assertFalse(response.is_error, (desc.operation_id, response.content))
                        code, payload = _response(desc.operation_id)
                        self.assertEqual(response.structured_content["status_code"], code)
                        expected = {"redacted": True} if desc.redacted_result else payload
                        self.assertEqual(response.structured_content["data"], expected)
                        called.append(desc.operation_id)
                self.assertEqual(len(called), 72)
                self.assertEqual(len(sent), 72)

    async def test_list_filters_scopes_and_call_reauthorizes(self) -> None:
        cfg = Settings.from_env({"YOUGILE_API_KEY": SECRET, "YOUGILE_COMPANY_ID": COMPANY})
        seen = []
        async with YouGileClient(
            cfg, transport=httpx.MockTransport(lambda request: seen.append(request)),
            limiter=_NoWaitLimiter(),
        ) as api:
            dispatcher = ToolDispatcher(api, company_id=COMPANY, project_resolver=_project)
            async def denied_principal(_: Any):
                return _principal(scopes=frozenset())
            server = make_mcp_server(dispatcher, resolve_principal=denied_principal)
            async with Client(server, raise_exceptions=True) as client:
                listed = await client.list_tools()
                tools = listed.tools if hasattr(listed, "tools") else listed
                self.assertEqual(len(tools), 0)
                board = build_registry().by_operation("BoardController_get")
                result = await client.call_tool(board.name, {"path": {"id": "board-1"}})
                self.assertTrue(result.is_error)
                self.assertIn("permission_denied", result.content[0].text)
                self.assertEqual(seen, [])


    async def test_protocol_negative_error_categories(self) -> None:
        cfg = Settings.from_env({"YOUGILE_API_KEY": SECRET, "YOUGILE_COMPANY_ID": COMPANY})
        registry = build_registry()
        task = registry.by_operation("TaskController_create")
        async def principal(_: Any):
            return _principal()
        for status, category in (
            (400, "vendor_validation"), (401, "authentication_failed"),
            (403, "permission_denied"), (404, "not_found"),
            (429, "rate_limited"), (500, "upstream_failure"),
        ):
            with self.subTest(status=status):
                requests = []
                def handler(request: httpx.Request) -> httpx.Response:
                    requests.append(request)
                    return httpx.Response(status, json={"message": "SECRET " + SECRET})
                async with YouGileClient(
                    cfg, transport=httpx.MockTransport(handler), limiter=_NoWaitLimiter(),
                ) as api:
                    dispatcher = ToolDispatcher(api, company_id=COMPANY, project_resolver=_project)
                    async with Client(
                        make_mcp_server(dispatcher, resolve_principal=principal),
                        raise_exceptions=True,
                    ) as sdk:
                        result = await sdk.call_tool(task.name, _arguments(task.operation_id))
                        self.assertTrue(result.is_error)
                        self.assertEqual(json.loads(result.content[0].text)["category"], category)
                        self.assertNotIn(SECRET, result.content[0].text)
                        self.assertEqual(len(requests), 1)

    async def test_protocol_invalid_input_admin_approval_and_unknown_tool(self) -> None:
        cfg = Settings.from_env({"YOUGILE_API_KEY": SECRET, "YOUGILE_COMPANY_ID": COMPANY})
        calls = []
        async def principal(_: Any):
            return _principal()
        async with YouGileClient(
            cfg, transport=httpx.MockTransport(lambda request: calls.append(request)),
            limiter=_NoWaitLimiter(),
        ) as api:
            dispatcher = ToolDispatcher(api, company_id=COMPANY, project_resolver=_project)
            registry = build_registry()
            async with Client(
                make_mcp_server(dispatcher, resolve_principal=principal),
                raise_exceptions=True,
            ) as sdk:
                for name, args, category in (
                    (registry.by_operation("TaskController_create").name, {"wrong": True}, "invalid_input"),
                    (registry.by_operation("CompanyController_update").name,
                     {"body": {"title": "changed"}}, "approval_required"),
                    ("yg_v2_unknown_name", {}, "unknown_tool"),
                ):
                    with self.subTest(category=category):
                        result = await sdk.call_tool(name, args)
                        self.assertTrue(result.is_error)
                        self.assertEqual(json.loads(result.content[0].text)["category"], category)
            self.assertEqual(calls, [])


def _route_matches(template: str, concrete: str) -> bool:
    # This helper is only mock response routing, never MCP production routing.
    import re
    return re.fullmatch(re.sub(r"\{[^{}]+\}", "[^/]+", template), concrete) is not None
