"""Account issuance using only our official YouGileClient and MockTransport."""

from __future__ import annotations

import json
import unittest

import httpx

from test_mcp_factory import _response

from yougile_mcp.cloud.yougile_signin import (
    CloudBadCredentials,
    CloudSignInError,
    CloudYouGileSignIn,
)
from yougile_mcp.config import Settings


class CloudSignInTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.sent = []
        self.company_returned = "company-A"
        self.fail_login = False
        self.fail_profile = False

        def handler(req):
            self.sent.append(req)
            path = req.url.path
            if req.method == "POST" and path == "/api-v2/auth/companies":
                if self.fail_login:
                    return httpx.Response(401, json={"message": "Password-EXAMPLE"})
                return httpx.Response(200, json={
                    "content": [
                        {"id": "company-A", "name": "Alpha", "isAdmin": True},
                        {"id": "company-B", "name": "Beta", "isAdmin": False},
                    ],
                    "paging": {"count": 2, "limit": 1000, "offset": 0, "next": False},
                })
            if req.method == "POST" and path == "/api-v2/auth/keys":
                data = json.loads(req.content)
                if data["companyId"] not in {"company-A", "company-B"}:
                    return httpx.Response(403, json={"message": "invalid company"})
                return httpx.Response(201, json={"key": "per-user-secret-key"})
            if req.method == "GET" and path == "/api-v2/companies":
                return httpx.Response(200, json={
                    "id": self.company_returned, "title": "Alpha", "timestamp": 42,
                })
            if req.method == "GET" and path == "/api-v2/users/me":
                if self.fail_profile:
                    return httpx.Response(403, json={"message": "forbidden"})
                _, profile = _response("UserController_getMe")
                return httpx.Response(200, json={
                    **profile,
                    "id": "user-1", "email": "person@example.test",
                    "realName": "Test User", "isAdmin": True,
                })
            if req.method == "DELETE" and path.startswith("/api-v2/auth/keys/"):
                return httpx.Response(200)
            raise AssertionError("Unrecognized mock request: " + str(req.url))

        self.signin = CloudYouGileSignIn(
            Settings.from_env({}), transport=httpx.MockTransport(handler),
        )

    async def test_company_choices_and_full_provisioning(self):
        companies = await self.signin.companies("person@example.test", "secret-password")
        self.assertEqual({c.id for c in companies}, {"company-A", "company-B"})
        result = await self.signin.provision(
            "person@example.test", "secret-password",
            selected_company_id="company-A",
        )
        self.assertEqual(result.company_id, "company-A")
        self.assertEqual(result.user_id, "user-1")
        self.assertEqual(result.name, "Test User")
        self.assertEqual(result.api_key.reveal(), "per-user-secret-key")
        self.assertNotIn("per-user-secret-key", repr(result))
        self.assertNotIn("secret-password", repr(result))
        self.assertTrue(any(
            req.headers.get("authorization") == "Bearer per-user-secret-key"
            for req in self.sent if req.method == "GET"
        ))

    async def test_reject_selected_company_outside_vendor_list_before_key_issue(self):
        with self.assertRaises(CloudSignInError):
            await self.signin.provision(
                "person@example.test", "secret-password",
                selected_company_id="foreign-company",
            )
        self.assertFalse(any(req.url.path == "/api-v2/auth/keys" for req in self.sent))

    async def test_wrong_password_returns_sanitized_failure(self):
        self.fail_login = True
        with self.assertRaises(CloudBadCredentials) as exc:
            await self.signin.companies("person@example.test", "secret-password")
        self.assertNotIn("Password-EXAMPLE", str(exc.exception))
        self.assertNotIn("secret-password", str(exc.exception))

    async def test_mismatched_key_company_is_revoked_and_not_stored(self):
        self.company_returned = "company-B"
        with self.assertRaises(CloudSignInError):
            await self.signin.provision(
                "person@example.test", "secret-password",
                selected_company_id="company-A",
            )
        self.assertEqual(
            sum(req.method == "DELETE" and req.url.path.startswith("/api-v2/auth/keys/")
                for req in self.sent),
            1,
        )
        self.assertFalse(any(req.url.path == "/api-v2/users/me" for req in self.sent))

    async def test_failed_profile_revokes_orphan_issued_key(self):
        self.fail_profile = True
        with self.assertRaises(Exception):
            await self.signin.provision(
                "person@example.test", "secret-password",
                selected_company_id="company-A",
            )
        self.assertTrue(any(req.method == "DELETE" for req in self.sent))

    def test_global_api_key_rejected_for_signin(self):
        with self.assertRaises(ValueError):
            CloudYouGileSignIn(Settings.from_env({
                "YOUGILE_API_KEY": "global-key",
                "YOUGILE_COMPANY_ID": "global-company",
            }))


if __name__ == "__main__":
    unittest.main()
