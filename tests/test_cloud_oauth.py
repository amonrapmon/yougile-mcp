"""GEN-231 OAuth provider: real PostgreSQL, Valkey and SDK auth data models."""
from __future__ import annotations

import os
import unittest
from urllib.parse import parse_qs, urlparse

from mcp.server.auth.provider import AuthorizationParams, AuthorizeError, RegistrationError, TokenError
from mcp.shared.auth import OAuthClientInformationFull
from yougile_mcp.cloud.crypto import CloudCipher, new_encryption_key
from yougile_mcp.cloud.oauth import CloudOAuthProvider
from yougile_mcp.cloud.persistence import PostgresCloudStore
from yougile_mcp.cloud.valkey import ValkeyCloudState
from yougile_mcp.cloud.yougile_signin import ProvisionedYouGileAccount
from yougile_mcp.config import Secret

DB = os.environ.get("TEST_CLOUD_DATABASE_URL")
KV = os.environ.get("TEST_CLOUD_VALKEY_URL")
PUBLIC_URL = "https://mcp.example.test"
RESOURCE = PUBLIC_URL + "/mcp"


@unittest.skipUnless(DB and KV, "requires Postgres/Redis CI services")
class CloudOAuthProviderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = PostgresCloudStore(DB, CloudCipher([new_encryption_key()]))
        await self.db.open()
        await self.db.migrate()
        async with self.db.pool.connection() as conn:
            await conn.execute(
                "TRUNCATE cloud_refresh_tokens,cloud_oauth_clients,cloud_users,"
                "cloud_companies,cloud_audit_log RESTART IDENTITY CASCADE"
            )
        self.kv = await ValkeyCloudState.connect(
            KV, namespace="oauth-test-" + os.urandom(8).hex() + ":",
        )
        self.oauth = CloudOAuthProvider(
            public_url=PUBLIC_URL, store=self.db, state=self.kv,
            jwt_secret="s" * 64, redirect_origins=("https://chatgpt.com",),
        )
        self.person = await self.db.save_account(
            ProvisionedYouGileAccount(
                company_id="c-main", user_id="vendor-person-1",
                email="safe@example.test", name="Person", is_admin=False,
                api_key=Secret("per-person-secret"),
            ),
            company_name="My Company",
        )
        self.client = OAuthClientInformationFull(
            client_id="cli-one", client_name="AI Client",
            redirect_uris=["https://chatgpt.com/callback"],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
        )
        await self.oauth.register_client(self.client)

    async def asyncTearDown(self):
        await self.kv.close()
        await self.db.close()

    async def _authorize(self):
        path = await self.oauth.authorize(
            self.client,
            AuthorizationParams(
                state="xyz", scopes=["yougile.full"],
                code_challenge="test_challenge_s256",
                redirect_uri="https://chatgpt.com/callback",
                redirect_uri_provided_explicitly=True,
                resource=RESOURCE,
            ),
        )
        flow = parse_qs(urlparse(path).query)["flow"][0]
        self.assertIsNotNone(await self.oauth.pending_request(flow))
        target = await self.oauth.finish_signin(
            flow, account_id=self.person.account_id,
        )
        query = parse_qs(urlparse(target).query)
        self.assertEqual(query["state"], ["xyz"])
        self.assertEqual(query["iss"], [PUBLIC_URL])
        self.assertIsNone(await self.oauth.pending_request(flow))
        return query["code"][0]

    async def test_registered_client_one_use_code_access_and_refresh(self):
        client = await self.oauth.get_client(self.client.client_id)
        self.assertEqual(client.client_id, self.client.client_id)
        code = await self._authorize()
        loaded = await self.oauth.load_authorization_code(self.client, code)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.subject, self.person.account_id)
        tokens = await self.oauth.exchange_authorization_code(self.client, loaded)
        self.assertEqual(tokens.token_type, "Bearer")
        self.assertTrue(tokens.refresh_token)
        self.assertIsNone(await self.oauth.load_authorization_code(self.client, code))
        claims = await self.oauth.verify_token(tokens.access_token)
        self.assertEqual(claims.subject, self.person.account_id)
        self.assertEqual(claims.resource, RESOURCE)
        self.assertEqual(claims.scopes, ["yougile.full"])

        refresh = await self.oauth.load_refresh_token(self.client, tokens.refresh_token)
        self.assertIsNotNone(refresh)
        later = await self.oauth.exchange_refresh_token(
            self.client, refresh, ["yougile.full"],
        )
        self.assertNotEqual(later.refresh_token, tokens.refresh_token)
        with self.assertRaises(TokenError):
            await self.oauth.exchange_refresh_token(self.client, refresh, ["yougile.full"])
        self.assertIsNotNone(await self.oauth.verify_token(later.access_token))
        await self.oauth.revoke_token(claims)
        self.assertIsNone(await self.oauth.verify_token(tokens.access_token))
        self.assertIsNone(await self.oauth.load_refresh_token(self.client, later.refresh_token))

    async def test_bearer_dies_after_company_disable_and_tamper(self):
        code = await self._authorize()
        tokens = await self.oauth.exchange_authorization_code(
            self.client, await self.oauth.load_authorization_code(self.client, code),
        )
        self.assertIsNotNone(await self.oauth.verify_token(tokens.access_token))
        self.assertIsNone(await self.oauth.verify_token(tokens.access_token + "tamper"))
        other_issuer = CloudOAuthProvider(
            public_url="https://other.example.test", store=self.db, state=self.kv,
            jwt_secret="s" * 64,
        )
        self.assertIsNone(await other_issuer.verify_token(tokens.access_token))
        await self.db.set_company_enabled("c-main", False)
        self.assertIsNone(await self.oauth.verify_token(tokens.access_token))
        await self.db.set_company_enabled("c-main", True)
        # Re-enabling a company must not resurrect previously issued JWTs.
        self.assertIsNone(await self.oauth.verify_token(tokens.access_token))
        new_tokens = await self.oauth._issue(
            user_id=int(self.person.account_id), client_id=self.client.client_id,
            scopes=["yougile.full"],
        )
        self.assertIsNotNone(await self.oauth.verify_token(new_tokens.access_token))

    async def test_bad_redirect_resource_scopes_and_disabled_actor_denied(self):
        evil = OAuthClientInformationFull(
            client_id="evil", redirect_uris=["https://chatgpt.com.evil.test/callback"],
        )
        with self.assertRaises(RegistrationError):
            await self.oauth.register_client(evil)
        with self.assertRaises(AuthorizeError):
            await self.oauth.authorize(
                self.client,
                AuthorizationParams(
                    state="xyz", scopes=["admin:all"], code_challenge="challenge",
                    redirect_uri="https://chatgpt.com/callback",
                    redirect_uri_provided_explicitly=True, resource=RESOURCE,
                ),
            )
        with self.assertRaises(AuthorizeError):
            await self.oauth.authorize(
                self.client,
                AuthorizationParams(
                    state="xyz", scopes=[], code_challenge="challenge",
                    redirect_uri="https://chatgpt.com/callback",
                    redirect_uri_provided_explicitly=True,
                    resource="https://other.example.test/mcp",
                ),
            )
        with self.assertRaises(TokenError):
            await self.oauth.finish_signin("unknown", account_id="invalid")
