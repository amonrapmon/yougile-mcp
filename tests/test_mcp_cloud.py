"""Multi-company cloud bridge: real SDK messages and isolated YouGile keys."""

from __future__ import annotations

import json
import unittest
from dataclasses import replace

import httpx
from mcp import Client

from yougile_mcp.config import Secret, Settings
from yougile_mcp.mcp.cloud import (
    CloudAccount,
    CloudTenantSessions,
    VerifiedCloudActor,
    make_cloud_mcp_server,
)
from yougile_mcp.mcp.factory import build_registry


class MemoryAccounts:
    def __init__(self):
        self.data = {
            "user-A": CloudAccount("company-A", Secret("api-key-A")),
            "user-B": CloudAccount("company-B", Secret("api-key-B")),
        }
        self.broken = False

    async def load(self, account_id):
        if self.broken:
            raise OSError("private database error")
        return self.data.get(account_id)


CURRENT_ACTOR = {"account_id": None}


async def resolve_actor(_context):
    user = CURRENT_ACTOR["account_id"]
    return VerifiedCloudActor(user) if user else None


def responses(req):
    key = req.headers.get("authorization")
    company_for_key = {
        "Bearer api-key-A": "company-A",
        "Bearer api-key-B": "company-B",
    }
    company = company_for_key.get(key)
    if company is None:
        return httpx.Response(401, json={"message": "untrusted key"})
    if req.url.path.startswith("/api-v2/companies"):
        return httpx.Response(200, json={"id": company, "title": "Test", "timestamp": 42})
    if req.method == "POST" and req.url.path == "/api-v2/projects":
        return httpx.Response(201, json={"id": "project-new-" + company})
    if req.url.path.startswith("/api-v2/boards/"):
        board_id = req.url.path.rsplit("/", 1)[-1]
        if board_id != "board-" + company:
            return httpx.Response(403, json={"message": "foreign board"})
        return httpx.Response(200, json={
            "id": board_id, "title": "Board", "projectId": "project-" + company,
        })
    raise AssertionError("Unexpected test request: " + str(req.url))


class CloudBridgeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.accounts = MemoryAccounts()
        self.requests = []

        def handler(request):
            self.requests.append(request)
            return responses(request)

        self.cfg = Settings.from_env({})
        self.registry = build_registry()
        self.sessions = CloudTenantSessions(
            self.cfg,
            resolve_actor=resolve_actor,
            accounts=self.accounts,
            registry=self.registry,
            transport=httpx.MockTransport(handler),
        )

    async def _invoke(self, client, actor, name, args):
        previous = CURRENT_ACTOR["account_id"]
        CURRENT_ACTOR["account_id"] = actor
        try:
            return await client.call_tool(name, args)
        finally:
            CURRENT_ACTOR["account_id"] = previous

    async def test_two_users_get_all_72_tools_and_separate_company_keys(self):
        server = make_cloud_mcp_server(self.sessions)
        descriptor = self.registry.by_operation("BoardController_get")
        company_get = self.registry.by_operation("BoardController_get")
        async with Client(server, raise_exceptions=True) as client:
            for actor in ("user-A", "user-B"):
                previous = CURRENT_ACTOR["account_id"]
                CURRENT_ACTOR["account_id"] = actor
                try:
                    listed = await client.list_tools()
                finally:
                    CURRENT_ACTOR["account_id"] = previous
                items = listed.tools if hasattr(listed, "tools") else listed
                self.assertEqual(len(items), 72)
                self.assertIn(descriptor.name, {item.name for item in items})

                suffix = "A" if actor == "user-A" else "B"
                res = await self._invoke(
                    client, actor, company_get.name,
                    {"path": {"id": "board-company-" + suffix}},
                )
                self.assertFalse(res.is_error, res.content)
                self.assertEqual(res.structured_content["data"]["projectId"], "project-company-" + suffix)

                res = await self._invoke(
                    client, actor, descriptor.name, {"path": {"id": "board-company-" + suffix}},
                )
                self.assertFalse(res.is_error, res.content)
                self.assertEqual(res.structured_content["data"]["projectId"], "project-company-" + suffix)
        self.assertTrue(any(req.headers.get("authorization") == "Bearer api-key-A" for req in self.requests))
        self.assertTrue(any(req.headers.get("authorization") == "Bearer api-key-B" for req in self.requests))

    async def test_title_only_project_create_works_in_cloud_without_approval_provider(self):
        tool = self.registry.by_operation("ProjectController_create")
        async with Client(make_cloud_mcp_server(self.sessions), raise_exceptions=True) as client:
            for actor, expected in (("user-A", "company-A"), ("user-B", "company-B")):
                with self.subTest(actor=actor):
                    result = await self._invoke(
                        client, actor, tool.name,
                        {"body": {"title": "Заявки", "idempotencyKey": "safe-" + actor}},
                    )
                    self.assertFalse(result.is_error, result.content)
                    self.assertEqual(result.structured_content["data"]["id"], "project-new-" + expected)
                    for field in ("users", "departments"):
                        denied = await self._invoke(
                            client, actor, tool.name,
                            {"body": {"title": "Заявки", field: {}}},
                        )
                        self.assertTrue(denied.is_error)
                        self.assertEqual(
                            json.loads(denied.content[0].text)["category"], "approval_required",
                        )
        posts = [req for req in self.requests if req.method == "POST"]
        self.assertEqual(len(posts), 2)
        self.assertEqual(
            {req.headers.get("authorization") for req in posts},
            {"Bearer api-key-A", "Bearer api-key-B"},
        )

    async def test_cross_company_board_denied_with_own_user_key(self):
        board = self.registry.by_operation("BoardController_get")
        async with Client(make_cloud_mcp_server(self.sessions), raise_exceptions=True) as client:
            res = await self._invoke(
                client, "user-A", board.name, {"path": {"id": "board-company-B"}},
            )
            self.assertTrue(res.is_error)
            self.assertIn("permission_denied", res.content[0].text)
            self.assertNotIn("api-key-A", res.content[0].text)
            self.assertFalse(any(
                r.headers.get("authorization") == "Bearer api-key-B"
                for r in self.requests
            ))

    async def test_anonymous_unknown_disabled_and_revoked_users(self):
        company = self.registry.by_operation("BoardController_get")
        async with Client(make_cloud_mcp_server(self.sessions), raise_exceptions=True) as client:
            for actor in (None, "missing"):
                res = await self._invoke(client, actor, company.name, {"path": {"id": "board-company-A"}})
                self.assertTrue(res.is_error)
                self.assertEqual(json.loads(res.content[0].text)["category"], "permission_denied")
            self.accounts.data["user-A"] = replace(
                self.accounts.data["user-A"], enabled=False
            )
            denied = await self._invoke(client, "user-A", company.name, {"path": {"id": "board-company-A"}})
            self.assertTrue(denied.is_error)
            self.accounts.broken = True
            denied = await self._invoke(client, "user-B", company.name, {"path": {"id": "board-company-B"}})
            self.assertTrue(denied.is_error)
        self.assertEqual(self.requests, [])

    async def test_company_key_mismatch_denied_before_tool_invocation(self):
        self.accounts.data["user-A"] = replace(
            self.accounts.data["user-A"], company_id="company-B"
        )
        company_get = self.registry.by_operation("BoardController_get")
        async with Client(make_cloud_mcp_server(self.sessions), raise_exceptions=True) as client:
            denied = await self._invoke(client, "user-A", company_get.name, {"path": {"id": "board-company-A"}})
            self.assertTrue(denied.is_error)
            self.assertIn("permission_denied", denied.content[0].text)
        self.assertEqual(len(self.requests), 1)  # company verifier only

    async def test_revocation_and_key_rotation_rechecked_per_request(self):
        company_get = self.registry.by_operation("BoardController_get")
        async with Client(make_cloud_mcp_server(self.sessions), raise_exceptions=True) as client:
            good = await self._invoke(client, "user-A", company_get.name, {"path": {"id": "board-company-A"}})
            self.assertFalse(good.is_error)
            self.accounts.data["user-A"] = replace(
                self.accounts.data["user-A"], api_key=Secret("revoked-key")
            )
            bad = await self._invoke(client, "user-A", company_get.name, {"path": {"id": "board-company-A"}})
            self.assertTrue(bad.is_error)
            self.assertEqual(json.loads(bad.content[0].text)["category"], "permission_denied")

    def test_global_api_key_is_rejected_for_hosted_runtime(self):
        configured = Settings.from_env({
            "YOUGILE_API_KEY": "global-secret",
            "YOUGILE_COMPANY_ID": "global-company",
        })
        with self.assertRaises(ValueError):
            CloudTenantSessions(
                configured,
                resolve_actor=resolve_actor,
                accounts=self.accounts,
            )


if __name__ == "__main__":
    unittest.main()
