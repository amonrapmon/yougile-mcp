"""GEN-231 identity and project resource ownership behavior against MockTransport."""

from __future__ import annotations

import unittest

import httpx

from test_mcp_factory import COMPANY, SECRET, _principal
from yougile_mcp.api import YouGileClient
from yougile_mcp.config import Settings
from yougile_mcp.mcp.dispatch import ToolDispatchError, ToolDispatcher
from yougile_mcp.mcp.factory import build_registry
from yougile_mcp.mcp.ownership import CompanyIdentityVerifier, ProjectOwnershipResolver

GOOD = "owned-project"
BAD = "other-project"


def _server_response(request: httpx.Request, *, provider_company: str = COMPANY) -> httpx.Response:
    path = request.url.path
    if path.startswith("/api-v2/companies"):
        return httpx.Response(200, json={
            "id": provider_company, "title": "Synthetic Company", "timestamp": 42,
        })
    if request.method == "GET" and "/api-v2/boards/" in path:
        board_id = path.rsplit("/", 1)[-1]
        return httpx.Response(200, json={
            "id": board_id, "title": "Board",
            "projectId": GOOD if board_id == "board-allowed" else BAD,
        })
    if request.method == "GET" and "/api-v2/columns/" in path:
        col_id = path.rsplit("/", 1)[-1]
        return httpx.Response(200, json={
            "id": col_id, "title": "Column",
            "boardId": "board-allowed" if col_id == "column-allowed" else "board-other",
        })
    if request.method == "GET" and "/api-v2/tasks/" in path:
        task_id = path.rsplit("/", 1)[-1]
        return httpx.Response(200, json={
            "id": task_id, "title": "Task", "timestamp": 42,
            "columnId": "column-allowed",
        })
    if request.method == "PUT" and "/api-v2/tasks/" in path:
        return httpx.Response(200, json={"id": path.rsplit("/", 1)[-1]})
    raise AssertionError("Unexpected backend request")


class VerifiedOwnershipTests(unittest.IsolatedAsyncioTestCase):
    async def test_company_binding_and_project_lineage(self):
        requests: list[httpx.Request] = []
        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return _server_response(request)

        cfg = Settings.from_env({
            "YOUGILE_API_KEY": SECRET, "YOUGILE_COMPANY_ID": COMPANY,
        })
        async with YouGileClient(cfg, transport=httpx.MockTransport(handler)) as client:
            verifier = CompanyIdentityVerifier(client, company_id=COMPANY)
            resolver = ProjectOwnershipResolver(client, company_id=COMPANY)
            dispatcher = ToolDispatcher(
                client, company_id=COMPANY, company_verifier=verifier,
                project_resolver=resolver,
            )
            principal = _principal(projects=frozenset({GOOD}), wide=False)
            board_tool = build_registry().by_operation("BoardController_get")
            allowed = await dispatcher.call(board_tool.name, {"path": {"id": "board-allowed"}}, principal)
            self.assertEqual(allowed["data"]["projectId"], GOOD)
            self.assertEqual(sum(req.url.path.startswith("/api-v2/companies") for req in requests), 1)

            before = len(requests)
            with self.assertRaises(ToolDispatchError) as denied:
                await dispatcher.call(board_tool.name, {"path": {"id": "board-other"}}, principal)
            self.assertEqual(denied.exception.category, "permission_denied")
            # One internal GET to verify ownership, but no second GET for the tool.
            self.assertEqual(len(requests), before + 1)
            self.assertEqual(requests[-1].method, "GET")

            task = build_registry().by_operation("TaskController_update")
            before = len(requests)
            with self.assertRaises(ToolDispatchError) as moved:
                await dispatcher.call(task.name, {
                    "path": {"id": "task-one"}, "body": {"columnId": "column-other"},
                }, principal)
            self.assertEqual(moved.exception.category, "permission_denied")
            self.assertFalse(any(req.method == "PUT" for req in requests[before:]))

            updated = await dispatcher.call(task.name, {
                "path": {"id": "task-one"}, "body": {"columnId": "column-allowed"},
            }, principal)
            self.assertEqual(updated["data"]["id"], "task-one")
            self.assertEqual(sum(req.method == "PUT" for req in requests), 1)
            # Verification is cached per client instance for bounded duration.
            self.assertEqual(sum(req.url.path.startswith("/api-v2/companies") for req in requests), 1)

    async def test_company_credential_mismatch_denied_before_resource_lookup(self):
        requests: list[httpx.Request] = []
        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return _server_response(request, provider_company="unrelated-tenant")

        cfg = Settings.from_env({
            "YOUGILE_API_KEY": SECRET, "YOUGILE_COMPANY_ID": COMPANY,
        })
        async with YouGileClient(cfg, transport=httpx.MockTransport(handler)) as client:
            dispatcher = ToolDispatcher(
                client, company_id=COMPANY,
                company_verifier=CompanyIdentityVerifier(client, company_id=COMPANY),
                project_resolver=ProjectOwnershipResolver(client, company_id=COMPANY),
            )
            desc = build_registry().by_operation("BoardController_get")
            principal = _principal(projects=frozenset({GOOD}), wide=False)
            with self.assertRaises(ToolDispatchError) as denied:
                await dispatcher.call(desc.name, {"path": {"id": "board-allowed"}}, principal)
            self.assertEqual(denied.exception.category, "permission_denied")
            self.assertEqual(len(requests), 1)
            self.assertTrue(requests[0].url.path.startswith("/api-v2/companies"))

    async def test_invalid_args_cannot_trigger_ownership_lookups(self):
        requests = []
        cfg = Settings.from_env({
            "YOUGILE_API_KEY": SECRET, "YOUGILE_COMPANY_ID": COMPANY,
        })
        async with YouGileClient(
            cfg, transport=httpx.MockTransport(lambda req: requests.append(req)),
        ) as client:
            dispatcher = ToolDispatcher(
                client, company_id=COMPANY,
                company_verifier=CompanyIdentityVerifier(client, company_id=COMPANY),
                project_resolver=ProjectOwnershipResolver(client, company_id=COMPANY),
            )
            tool = build_registry().by_operation("BoardController_get")
            with self.assertRaises(ToolDispatchError) as exc:
                await dispatcher.call(
                    tool.name, {"path": {}},
                    _principal(projects=frozenset({GOOD}), wide=False),
                )
            self.assertEqual(exc.exception.category, "invalid_input")
            self.assertEqual(requests, [])

    def test_global_resources_have_no_fictional_project_scope(self):
        registry = build_registry()
        for item in registry.list():
            if item.operation_id.startswith((
                "StringSticker", "SprintSticker", "ChatMessage", "GroupChat",
            )):
                with self.subTest(operation=item.operation_id):
                    self.assertEqual(item.resource_scope, "company")


if __name__ == "__main__":
    unittest.main()
