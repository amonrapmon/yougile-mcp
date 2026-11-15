"""Exact host-operator allowlist and tenant actions, using the real admin HTTP fixture."""

from __future__ import annotations

import test_cloud_admin as company_tests

from yougile_mcp.cloud.yougile_signin import ProvisionedYouGileAccount
from yougile_mcp.config import Secret


class HostHTTPTests(company_tests.AdminHTTPTests):
    """Runs the company-admin regressions plus owner-only host actions."""

    host_subjects = ("company-A:admin-vendor",)

    async def _other_company(self):
        return await self.store.save_account(
            ProvisionedYouGileAccount(
                company_id="company-B", user_id="friend-user",
                email="friend@example.test", name="Friend",
                is_admin=False, api_key=Secret("key-friend"),
            ),
            company_name="Beta",
        )

    async def test_host_only_explicit_actor_access(self):
        await self._other_company()
        self.signin.multiple = True
        await self.login(company="company-B")
        forbidden = await self.http.get("/host")
        self.assertEqual(forbidden.status_code, 403)
        self.assertIn("Доступ запрещён", forbidden.text)
        other = await self.http.post(
            "/host/companies/company-A/disable", data={"csrf": "bogus"},
            headers={"Origin": "https://mcp.example.test"},
        )
        self.assertEqual(other.status_code, 403)
        self.assertTrue((await self.store.get_company("company-A"))["enabled"])

    async def test_host_dashboard_company_disable_and_reenable(self):
        friend = await self._other_company()
        self.assertIsNotNone(await self.store.load(friend.account_id))
        await self.login(company="company-A")
        dashboard = await self.http.get("/host")
        self.assertEqual(dashboard.status_code, 200, dashboard.text)
        self.assertIn("Компании на сервере", dashboard.text)
        self.assertIn("Beta", dashboard.text)
        index_csrf = self._csrf(dashboard.text)
        self.assertEqual((await self.http.post(
            "/host/companies/company-A/disable", data={"csrf": index_csrf},
            headers={"Origin": "https://mcp.example.test"},
        )).status_code, 403)
        disabled = await self.http.post(
            "/host/companies/company-B/disable", data={"csrf": index_csrf},
            headers={"Origin": "https://mcp.example.test"},
        )
        self.assertEqual(disabled.status_code, 303, disabled.text)
        self.assertIsNone(await self.store.load(friend.account_id))
        enabled = await self.http.post(
            "/host/companies/company-B/enable", data={"csrf": index_csrf},
            headers={"Origin": "https://mcp.example.test"},
        )
        self.assertEqual(enabled.status_code, 303, enabled.text)
        self.assertIsNotNone(await self.store.load(friend.account_id))
        self.assertEqual(
            (await self.store.get_company("company-B"))["id"], "company-B",
        )

    async def test_host_can_manage_other_company_members_with_scoped_queries(self):
        friend = await self._other_company()
        await self.login()
        company = await self.http.get("/host/companies/company-B")
        self.assertEqual(company.status_code, 200)
        self.assertIn("Friend", company.text)
        self.assertNotIn("key-friend", company.text)
        csrf = self._csrf(company.text)
        blocked = await self.http.post(
            "/host/companies/company-B/members/friend-user/block",
            data={"csrf": csrf}, headers={"Origin": "https://mcp.example.test"},
        )
        self.assertEqual(blocked.status_code, 303, blocked.text)
        self.assertTrue(await self.store.is_member_blocked("company-B", "friend-user"))
        self.assertIsNone(await self.store.load(friend.account_id))
        self.assertIn("key-friend", self.signin.revoked)
        self.assertFalse(await self.store.is_member_blocked("company-A", "friend-user"))
        # Ban cannot be bypassed by reconnecting.
        with self.assertRaises(ValueError):
            await self.store.save_account(
                ProvisionedYouGileAccount(
                    company_id="company-B", user_id="friend-user",
                    email="friend@example.test", name="Friend",
                    is_admin=False, api_key=Secret("fresh-key"),
                ),
                company_name="Beta",
            )
        clear = await self.http.post(
            "/host/companies/company-B/members/friend-user/unblock",
            data={"csrf": csrf}, headers={"Origin": "https://mcp.example.test"},
        )
        self.assertEqual(clear.status_code, 303, clear.text)
        self.assertFalse(await self.store.is_member_blocked("company-B", "friend-user"))

    async def test_host_actions_fail_closed_on_unknown_ids_and_missing_csrf(self):
        await self._other_company()
        await self.login()
        missing = await self.http.get("/host/companies/not-real")
        self.assertEqual(missing.status_code, 404)
        denied = await self.http.post(
            "/host/companies/company-B/disable",
            data={"csrf": "wrong"}, headers={"Origin": "https://mcp.example.test"},
        )
        self.assertEqual(denied.status_code, 403)
        dashboard = await self.http.get("/host")
        unknown = await self.http.post(
            "/host/companies/company-B/members/unknown-user/block",
            data={"csrf": self._csrf(dashboard.text)},
            headers={"Origin": "https://mcp.example.test"},
        )
        self.assertEqual(unknown.status_code, 404)

    async def test_vendor_admin_revocation_precedes_host_access(self):
        await self.login()
        self.admin_rights = False
        result = await self.http.get("/host")
        self.assertEqual(result.status_code, 403)
