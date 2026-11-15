"""Indalo company admin: real HTTP forms and PostgreSQL tenant boundaries."""

from __future__ import annotations

import asyncio
import os
import re
import unittest

import httpx
from test_mcp_factory import _response

from yougile_mcp.cloud.crypto import CloudCipher, new_encryption_key
from yougile_mcp.cloud.oauth import CloudOAuthProvider
from yougile_mcp.cloud.persistence import PostgresCloudStore
from yougile_mcp.cloud.valkey import ValkeyCloudState
from yougile_mcp.cloud.web import make_cloud_http_app
from yougile_mcp.cloud.yougile_signin import (
    ProvisionedYouGileAccount, YouGileCompanyChoice,
)
from yougile_mcp.config import Secret, Settings


DATABASE = os.environ.get("TEST_CLOUD_DATABASE_URL")
VALKEY = os.environ.get("TEST_CLOUD_VALKEY_URL")
ORIGIN = "https://mcp.example.test"


class FakeAdminSignin:
    def __init__(self):
        self.admin = True
        self.revoked = []
        self.multiple = False

    async def companies(self, login, password):
        if self.multiple:
            return (
                YouGileCompanyChoice("company-A", "Alpha", True),
                YouGileCompanyChoice("company-B", "Beta", True),
            )
        return (YouGileCompanyChoice("company-A", "Alpha", True),)

    async def provision(self, login, password, *, selected_company_id):
        return ProvisionedYouGileAccount(
            company_id=selected_company_id, user_id="admin-vendor",
            name="Admin Name", email=login, is_admin=self.admin,
            api_key=Secret("key-" + selected_company_id),
        )

    async def revoke_key(self, key):
        self.revoked.append(key)


@unittest.skipUnless(DATABASE and VALKEY, "requires PostgreSQL and Redis services")
class AdminHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.settings = Settings.from_env({
            "MCP_TRANSPORT": "http", "MCP_AUTH_MODE": "required",
            "MCP_PUBLIC_URL": ORIGIN, "MCP_HOST": "127.0.0.1",
        })
        self.store = PostgresCloudStore(DATABASE, CloudCipher([new_encryption_key()]))
        await self.store.open()
        await self.store.migrate()
        async with self.store.pool.connection() as conn:
            await conn.execute(
                "TRUNCATE cloud_member_blocks, cloud_refresh_tokens,cloud_oauth_clients,"
                "cloud_users,cloud_companies,cloud_audit_log RESTART IDENTITY CASCADE"
            )
        self.state = await ValkeyCloudState.connect(
            VALKEY, namespace="admin-" + os.urandom(8).hex() + ":",
        )
        self.oauth = CloudOAuthProvider(
            public_url=ORIGIN, store=self.store, state=self.state, jwt_secret="s" * 64,
        )
        self.signin = FakeAdminSignin()
        self.admin_rights = True
        self.calls = []

        _, admin_profile = _response("UserController_getMe")
        _, search_data = _response("UserController_search")
        _, company_dto = _response("CompanyController_get")

        def vendor(req):
            self.calls.append(req)
            token = req.headers.get("authorization")
            company = {
                "Bearer key-company-A": "company-A",
                "Bearer key-company-B": "company-B",
            }.get(token)
            if company is None:
                return httpx.Response(401, json={"error": "invalid key"})
            if req.url.path == "/api-v2/companies":
                return httpx.Response(200, json={
                    **company_dto, "id": company, "title": company,
                })
            if req.url.path == "/api-v2/users/me":
                return httpx.Response(200, json={
                    **admin_profile, "id": "admin-vendor", "isAdmin": self.admin_rights,
                    "realName": "Admin Name", "email": "admin@example.test",
                })
            if req.url.path == "/api-v2/users":
                return httpx.Response(200, json={
                    **search_data,
                    "content": [
                        {**admin_profile, "id": "admin-vendor",
                         "realName": "Admin Name", "email": "admin@example.test",
                         "isAdmin": self.admin_rights},
                        {**admin_profile, "id": "member-1",
                         "realName": '<img src=x onerror="alert(1)">',
                         "email": "member@example.test", "isAdmin": False},
                    ],
                    "paging": {"count": 2, "limit": 1000, "offset": 0, "next": False},
                })
            raise AssertionError("Unexpected API operation: " + str(req.url))

        app = make_cloud_http_app(
            settings=self.settings, provider=self.oauth, signin=self.signin,
            store=self.store, state=self.state, cipher=self.store._cipher,
            csrf_secret="s" * 64, yougile_transport=httpx.MockTransport(vendor),
        )
        self.started = asyncio.Event()
        self.stop = asyncio.Event()

        async def lifetime():
            # MCP SDK AnyIO group must close in the same task where it opens.
            async with app.router.lifespan_context(app):
                self.started.set()
                await self.stop.wait()

        self.lifespan = asyncio.create_task(lifetime())
        await self.started.wait()
        self.http = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=ORIGIN, follow_redirects=False,
        )

    async def asyncTearDown(self):
        await self.http.aclose()
        self.stop.set()
        await self.lifespan
        await self.state.close()
        await self.store.close()

    @staticmethod
    def _csrf(html):
        found = re.search(r'name="csrf" value="([0-9a-f]+)"', html)
        assert found, html[:350]
        return found.group(1)

    async def login(self, *, company="company-A"):
        page = await self.http.get("/admin/login")
        self.assertEqual(page.status_code, 200)
        result = await self.http.post(
            "/admin/login",
            data={"csrf": self._csrf(page.text),
                  "login": "admin@example.test", "password": "pass"},
            headers={"Origin": ORIGIN},
        )
        if self.signin.multiple:
            self.assertEqual(result.status_code, 200, result.text)
            self.assertIn("Выберите компанию", result.text)
            result = await self.http.post(
                "/admin/login/company",
                data={"csrf": self._csrf(result.text), "company": company},
                headers={"Origin": ORIGIN},
            )
        self.assertEqual(result.status_code, 303, result.text)
        self.assertEqual(result.headers["location"], "/admin")
        self.assertIn("__Host-ygc-admin", self.http.cookies)

    async def test_admin_signin_and_indalo_users_cards_settings(self):
        self.assertEqual((await self.http.get("/admin")).status_code, 303)
        await self.login()
        users = await self.http.get("/admin")
        self.assertEqual(users.status_code, 200, users.text)
        self.assertIn("Сотрудники", users.text)
        self.assertIn("Настроить", users.text)
        self.assertIn("&lt;img src=x", users.text)
        self.assertNotIn('<img src=x onerror="alert(1)">', users.text)
        settings = await self.http.get("/admin/settings")
        self.assertEqual(settings.status_code, 200)
        self.assertIn("Настройки компании", settings.text)
        self.assertIn("Full Access", settings.text)
        card = await self.http.get("/admin/users/member-1")
        self.assertEqual(card.status_code, 200)
        self.assertIn("Запретить подключение", card.text)

    async def test_csrf_origin_forgery_rejected_before_vendor_traffic(self):
        page = await self.http.get("/admin/login")
        self.assertEqual((await self.http.post(
            "/admin/login",
            data={"csrf": "bad", "login": "admin@example.test", "password": "p"},
            headers={"Origin": ORIGIN},
        )).status_code, 403)
        self.assertEqual((await self.http.post(
            "/admin/login",
            data={"csrf": self._csrf(page.text), "login": "admin@example.test", "password": "p"},
            headers={"Origin": "https://evil.example.test"},
        )).status_code, 403)
        self.assertEqual(self.calls, [])
        await self.login()
        person = await self.http.get("/admin/users/member-1")
        self.assertEqual((await self.http.post(
            "/admin/users/member-1/block", data={"csrf": "bad"},
            headers={"Origin": ORIGIN},
        )).status_code, 403)
        self.assertEqual((await self.http.post(
            "/admin/users/member-1/block",
            data={"csrf": self._csrf(person.text)},
            headers={"Origin": "https://evil.example.test"},
        )).status_code, 403)
        self.assertFalse(await self.store.is_member_blocked("company-A", "member-1"))

    async def test_unconnected_member_block_survives_login_and_unblock(self):
        await self.login()
        card = await self.http.get("/admin/users/member-1")
        result = await self.http.post(
            "/admin/users/member-1/block",
            data={"csrf": self._csrf(card.text)}, headers={"Origin": ORIGIN},
        )
        self.assertEqual(result.status_code, 303, result.text)
        self.assertTrue(await self.store.is_member_blocked("company-A", "member-1"))
        with self.assertRaises(ValueError):
            await self.store.save_account(
                ProvisionedYouGileAccount(
                    company_id="company-A", user_id="member-1",
                    email="member@example.test", name="Member",
                    is_admin=False, api_key=Secret("key-member"),
                ),
                company_name="Alpha",
            )
        card = await self.http.get("/admin/users/member-1")
        self.assertIn("Разрешить подключение", card.text)
        result = await self.http.post(
            "/admin/users/member-1/unblock",
            data={"csrf": self._csrf(card.text)}, headers={"Origin": ORIGIN},
        )
        self.assertEqual(result.status_code, 303, result.text)
        self.assertFalse(await self.store.is_member_blocked("company-A", "member-1"))

    async def test_disconnect_removes_key_and_refresh_and_revokes_vendor_key(self):
        await self.login()
        member = ProvisionedYouGileAccount(
            company_id="company-A", user_id="member-1", email="member@example.test",
            name="Member", is_admin=False, api_key=Secret("member-vendor-key"),
        )
        record = await self.store.save_account(member, company_name="Alpha")
        page = await self.http.get("/admin/users/member-1")
        self.assertIn("Отключить от YouGile MCP", page.text)
        gone = await self.http.post(
            "/admin/users/member-1/disconnect",
            data={"csrf": self._csrf(page.text)}, headers={"Origin": ORIGIN},
        )
        self.assertEqual(gone.status_code, 303, gone.text)
        self.assertIsNone(await self.store.load(record.account_id))
        self.assertIn("member-vendor-key", self.signin.revoked)

    async def test_admin_cannot_block_admin_and_lost_rights_end_session(self):
        await self.login()
        card = await self.http.get("/admin/users/admin-vendor")
        self.assertNotIn("Запретить подключение", card.text)
        denied = await self.http.post(
            "/admin/users/admin-vendor/block",
            data={"csrf": self._csrf(card.text)}, headers={"Origin": ORIGIN},
        )
        self.assertEqual(denied.status_code, 403)
        self.admin_rights = False
        forbidden = await self.http.get("/admin")
        self.assertEqual(forbidden.status_code, 403)
        self.assertIn("Нет прав администратора", forbidden.text)

    async def test_hostile_cross_company_id_cannot_mutate_another_company(self):
        await self.store.save_account(ProvisionedYouGileAccount(
            company_id="company-B", user_id="foreign-member",
            email="f@example.test", name="Foreign",
            is_admin=False, api_key=Secret("key-foreign"),
        ), company_name="Beta")
        await self.login()
        own = await self.http.get("/admin/users/member-1")
        blocked = await self.http.post(
            "/admin/users/foreign-member/block",
            data={"csrf": self._csrf(own.text)}, headers={"Origin": ORIGIN},
        )
        self.assertEqual(blocked.status_code, 404)
        self.assertIsNotNone(await self.store.company_member("company-B", "foreign-member"))
        self.assertFalse(await self.store.is_member_blocked("company-B", "foreign-member"))

    async def test_disabled_company_rejects_admin_session(self):
        await self.login()
        await self.store.set_company_enabled("company-A", False)
        result = await self.http.get("/admin")
        self.assertEqual(result.status_code, 303)
        self.assertEqual(result.headers["location"], "/admin/login")

    async def test_multi_company_admin_choice_scopes_session(self):
        self.signin.multiple = True
        await self.login(company="company-B")
        listing = await self.http.get("/admin")
        self.assertEqual(listing.status_code, 200, listing.text)
        self.assertIn("Beta", listing.text)
        self.assertEqual(self.calls[-1].headers["authorization"], "Bearer key-company-B")


if __name__ == "__main__":
    unittest.main()
