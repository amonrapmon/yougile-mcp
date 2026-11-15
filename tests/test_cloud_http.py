"""HTTP login/OAuth/streamable boundary through real PostgreSQL and Valkey."""
from __future__ import annotations

import base64
import hashlib
import os
import re
import unittest
from urllib.parse import parse_qs, urlparse

import httpx
from mcp.shared.auth import OAuthClientInformationFull

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
RESOURCE = ORIGIN + "/mcp"
VERIFIER = "secure-verifier-" + ("x" * 50)
CHALLENGE = base64.urlsafe_b64encode(
    hashlib.sha256(VERIFIER.encode()).digest()
).decode().rstrip("=")


class FakeYouGileLogin:
    def __init__(self):
        self.revoked = []
        self.used = []
        self.company_choices = (
            YouGileCompanyChoice("company-A", "Alpha", True),
            YouGileCompanyChoice("company-B", "Beta", False),
        )

    async def companies(self, login, password):
        self.used.append((login, password))
        return self.company_choices

    async def provision(self, login, password, *, selected_company_id):
        if selected_company_id not in {c.id for c in self.company_choices}:
            raise AssertionError("Company was not authorized by the vendor")
        return ProvisionedYouGileAccount(
            company_id=selected_company_id, user_id="user-" + login,
            name=login, email=login, is_admin=False,
            api_key=Secret("key-" + selected_company_id),
        )

    async def revoke_key(self, key):
        self.revoked.append(key)


@unittest.skipUnless(DATABASE and VALKEY, "requires disposable PostgreSQL/Redis CI services")
class CloudHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.settings = Settings.from_env({
            "MCP_TRANSPORT": "http", "MCP_AUTH_MODE": "required",
            "MCP_PUBLIC_URL": ORIGIN, "MCP_HOST": "127.0.0.1",
        })
        self.cipher = CloudCipher([new_encryption_key()])
        self.store = PostgresCloudStore(DATABASE, self.cipher)
        await self.store.open()
        await self.store.migrate()
        async with self.store.pool.connection() as conn:
            await conn.execute(
                "TRUNCATE cloud_refresh_tokens,cloud_oauth_clients,cloud_users,"
                "cloud_companies,cloud_audit_log RESTART IDENTITY CASCADE"
            )
        self.state = await ValkeyCloudState.connect(
            VALKEY, namespace="web-" + os.urandom(8).hex() + ":",
        )
        self.oauth = CloudOAuthProvider(
            public_url=ORIGIN, store=self.store, state=self.state,
            jwt_secret="s" * 64, redirect_origins=("https://chatgpt.com",),
        )
        self.signin = FakeYouGileLogin()
        self.requests = []

        def yougile(req):
            self.requests.append(req)
            token = req.headers.get("authorization")
            if token not in {"Bearer key-company-A", "Bearer key-company-B"}:
                return httpx.Response(401, json={"error": "invalid vendor token"})
            company = token.removeprefix("Bearer key-")
            if req.url.path == "/api-v2/companies":
                return httpx.Response(200, json={
                    "id": company, "title": company, "timestamp": 42,
                })
            return httpx.Response(404)

        app = make_cloud_http_app(
            settings=self.settings, provider=self.oauth, signin=self.signin,
            store=self.store, state=self.state, cipher=self.cipher,
            csrf_secret="s" * 64, yougile_transport=httpx.MockTransport(yougile),
        )
        self.lifespan = app.router.lifespan_context(app)
        await self.lifespan.__aenter__()
        self.http = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url=ORIGIN, follow_redirects=False,
        )
        self.client_id = "test-public-client"
        await self.oauth.register_client(OAuthClientInformationFull(
            client_id=self.client_id, client_name="ChatGPT",
            token_endpoint_auth_method="none",
            redirect_uris=["https://chatgpt.com/oauth/callback"],
            response_types=["code"], grant_types=["authorization_code", "refresh_token"],
            scope="yougile.full",
        ))

    async def asyncTearDown(self):
        await self.http.aclose()
        await self.lifespan.__aexit__(None, None, None)
        await self.state.close()
        await self.store.close()

    async def _start(self):
        response = await self.http.get("/authorize", params={
            "client_id": self.client_id,
            "redirect_uri": "https://chatgpt.com/oauth/callback",
            "response_type": "code", "code_challenge": CHALLENGE,
            "code_challenge_method": "S256", "scope": "yougile.full",
            "state": "123abc", "resource": RESOURCE,
        })
        self.assertEqual(response.status_code, 302, response.text)
        self.assertTrue(response.headers["location"].startswith(ORIGIN + "/signin?"))
        return response.headers["location"]

    async def _access(self, company="company-A"):
        path = await self._start()
        page = await self.http.get(path)
        self.assertEqual(page.status_code, 200)
        csrf = re.search(r'name="csrf" value="([0-9a-f]+)"', page.text).group(1)
        flow = parse_qs(urlparse(path).query)["flow"][0]
        signin = await self.http.post(
            "/signin", data={
                "csrf": csrf, "flow": flow,
                "login": "friend@example.test", "password": "example-pass",
            }, headers={"Origin": ORIGIN},
        )
        self.assertEqual(signin.status_code, 200, signin.text)
        self.assertIn("Выберите компанию", signin.text)
        self.assertNotIn("example-pass", signin.text)
        csrf2 = re.search(r'name="csrf" value="([0-9a-f]+)"', signin.text).group(1)
        chosen = await self.http.post(
            "/signin/company",
            data={"csrf": csrf2, "flow": flow, "company": company},
            headers={"Origin": ORIGIN},
        )
        self.assertEqual(chosen.status_code, 302, chosen.text)
        destination = urlparse(chosen.headers["location"])
        self.assertEqual(destination.hostname, "chatgpt.com")
        code = parse_qs(destination.query)["code"][0]
        self.assertEqual(parse_qs(destination.query)["state"], ["123abc"])
        token = await self.http.post("/token", data={
            "grant_type": "authorization_code", "client_id": self.client_id,
            "code": code, "code_verifier": VERIFIER,
            "redirect_uri": "https://chatgpt.com/oauth/callback", "resource": RESOURCE,
        })
        self.assertEqual(token.status_code, 200, token.text)
        return token.json(), code

    async def test_no_anonymous_mcp_and_metadata(self):
        for path in ("/.well-known/oauth-authorization-server", "/.well-known/oauth-protected-resource/mcp"):
            result = await self.http.get(path)
            self.assertEqual(result.status_code, 200, (path, result.text))
        for headers in ({}, {"Authorization": "Bearer made-up-token"}):
            result = await self.http.post(
                "/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                headers={"Accept": "application/json, text/event-stream", **headers},
            )
            self.assertEqual(result.status_code, 401)
        self.assertEqual(self.requests, [])

    async def test_csrf_origin_missing_flow_and_unsafe_redirect(self):
        self.assertEqual((await self.http.get("/signin?flow=invalid")).status_code, 400)
        path = await self._start()
        page = await self.http.get(path)
        csrf = re.search(r'name="csrf" value="([0-9a-f]+)"', page.text).group(1)
        flow = parse_qs(urlparse(path).query)["flow"][0]
        data = {"flow": flow, "csrf": csrf, "login": "user@example.test", "password": "pw"}
        self.assertEqual((await self.http.post(
            "/signin", data={**data, "csrf": "invalid"}, headers={"Origin": ORIGIN},
        )).status_code, 403)
        self.assertEqual((await self.http.post(
            "/signin", data=data, headers={"Origin": "https://evil.example"},
        )).status_code, 403)
        self.assertEqual((await self.http.post(
            "/signin", data=data, headers={"Origin": "null"},
        )).status_code, 403)
        self.assertEqual(self.signin.used, [])

    async def test_complete_oauth_login_refresh_and_mcp_tool_listing(self):
        token, code = await self._access()
        self.assertIn("access_token", token)
        self.assertIn("refresh_token", token)
        claims = await self.oauth.verify_token(token["access_token"])
        self.assertEqual(claims.scopes, ["yougile.full"])
        self.assertEqual((await self.http.post("/token", data={
            "grant_type": "authorization_code", "client_id": self.client_id,
            "code": code, "code_verifier": VERIFIER,
            "redirect_uri": "https://chatgpt.com/oauth/callback",
        })).status_code, 400)
        answer = await self.http.post(
            "/mcp",
            headers={
                "Authorization": "Bearer " + token["access_token"],
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2025-06-18", "capabilities": {},
                "clientInfo": {"name": "http-test", "version": "1"},
            }},
        )
        self.assertEqual(answer.status_code, 200, answer.text)
        self.assertIn("result", answer.json())
        listed = await self.http.post(
            "/mcp",
            headers={
                "Authorization": "Bearer " + token["access_token"],
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(len(listed.json()["result"]["tools"]), 72)
        refreshed = await self.http.post("/token", data={
            "grant_type": "refresh_token", "client_id": self.client_id,
            "refresh_token": token["refresh_token"],
        })
        self.assertEqual(refreshed.status_code, 200, refreshed.text)
        replay = await self.http.post("/token", data={
            "grant_type": "refresh_token", "client_id": self.client_id,
            "refresh_token": token["refresh_token"],
        })
        self.assertEqual(replay.status_code, 400)
        self.assertEqual(replay.json()["error"], "invalid_grant")

    async def test_company_key_is_different_for_other_company(self):
        a, _ = await self._access(company="company-A")
        b, _ = await self._access(company="company-B")
        ac = await self.oauth.verify_token(a["access_token"])
        bc = await self.oauth.verify_token(b["access_token"])
        self.assertNotEqual(ac.subject, bc.subject)
        self.assertEqual((await self.store.load(ac.subject)).company_id, "company-A")
        self.assertEqual((await self.store.load(bc.subject)).company_id, "company-B")
        await self.store.set_company_enabled("company-A", False)
        self.assertIsNone(await self.oauth.verify_token(a["access_token"]))
        self.assertIsNotNone(await self.oauth.verify_token(b["access_token"]))


if __name__ == "__main__":
    unittest.main()
