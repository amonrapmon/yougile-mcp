"""PostgreSQL/Valkey integration plus always-on credential crypto tests."""
from __future__ import annotations

import os
import unittest
from datetime import UTC, datetime, timedelta

from yougile_mcp.cloud.crypto import CloudCipher, hash_token, new_encryption_key
from yougile_mcp.cloud.yougile_signin import ProvisionedYouGileAccount
from yougile_mcp.config import Secret

DATABASE = os.environ.get("TEST_CLOUD_DATABASE_URL")
VALKEY = os.environ.get("TEST_CLOUD_VALKEY_URL")


def _person(company, key):
    return ProvisionedYouGileAccount(
        company_id=company, user_id="person-1", email="p@example.test",
        name="Test", is_admin=False, api_key=Secret(key),
    )


class CloudCryptoTests(unittest.TestCase):
    def test_key_encryption_rotation_and_no_plaintext(self):
        first, second = new_encryption_key(), new_encryption_key()
        token = CloudCipher([first]).encrypt(Secret("private-key-123"))
        self.assertNotIn(b"private-key-123", token)
        self.assertEqual(CloudCipher([first]).decrypt(token).reveal(), "private-key-123")
        with self.assertRaises(ValueError):
            CloudCipher([second]).decrypt(token)
        updated = CloudCipher([second, first]).rotate(token)
        self.assertEqual(CloudCipher([second]).decrypt(updated).reveal(), "private-key-123")

    def test_invalid_cipher_and_hash(self):
        with self.assertRaises(ValueError):
            CloudCipher([])
        with self.assertRaises(ValueError):
            CloudCipher(["not-valid"])
        self.assertNotEqual(hash_token("one"), hash_token("two"))


@unittest.skipUnless(DATABASE, "requires TEST_CLOUD_DATABASE_URL")
class CloudPostgresTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from yougile_mcp.cloud.persistence import PostgresCloudStore
        self.store = PostgresCloudStore(DATABASE, CloudCipher([new_encryption_key()]))
        await self.store.open()
        await self.store.migrate()
        async with self.store.pool.connection() as conn:
            await conn.execute(
                "TRUNCATE cloud_refresh_tokens,cloud_oauth_clients,cloud_users,"
                "cloud_companies,cloud_audit_log RESTART IDENTITY CASCADE"
            )

    async def asyncTearDown(self):
        await self.store.close()

    async def test_user_company_isolation_rotation_and_revocation(self):
        a = await self.store.save_account(_person("company-A", "key-A"), company_name="Alpha")
        b = await self.store.save_account(_person("company-B", "key-B"), company_name="Beta")
        self.assertNotEqual(a.account_id, b.account_id)
        self.assertIsNone(a.previous_api_key)
        self.assertEqual((await self.store.load(a.account_id)).api_key.reveal(), "key-A")
        self.assertEqual((await self.store.load(b.account_id)).api_key.reveal(), "key-B")
        self.assertIsNone(await self.store.load("not-a-number"))
        rotated = await self.store.save_account(
            _person("company-A", "key-A-new"), company_name="Alpha"
        )
        self.assertEqual(rotated.account_id, a.account_id)
        self.assertEqual(rotated.previous_api_key.reveal(), "key-A")
        self.assertEqual((await self.store.load(a.account_id)).api_key.reveal(), "key-A-new")
        await self.store.set_company_enabled("company-A", False)
        self.assertIsNone(await self.store.load(a.account_id))
        self.assertIsNotNone(await self.store.load(b.account_id))
        await self.store.set_user_enabled(b.account_id, False)
        self.assertIsNone(await self.store.load(b.account_id))
        await self.store.set_company_enabled("company-A", True)
        self.assertIsNotNone(await self.store.load(a.account_id))

    async def test_oauth_refresh_atomic_rotation_and_client_storage(self):
        person = await self.store.save_account(
            _person("company-A", "key-A"), company_name="Alpha"
        )
        await self.store.save_oauth_client("client-1", {"client_id": "client-1"})
        self.assertEqual((await self.store.get_oauth_client("client-1"))["client_id"], "client-1")
        await self.store.save_refresh(
            "refresh-opaque", user_id=int(person.account_id), client_id="client-1",
            scopes=["read"], resource=None,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        async with self.store.pool.connection() as conn:
            record = await (await conn.execute(
                "SELECT token_hash FROM cloud_refresh_tokens"
            )).fetchone()
        self.assertEqual(record["token_hash"], hash_token("refresh-opaque"))
        self.assertNotEqual(record["token_hash"], "refresh-opaque")
        self.assertEqual((await self.store.take_refresh("refresh-opaque"))["client_id"], "client-1")
        self.assertIsNone(await self.store.take_refresh("refresh-opaque"))
        await self.store.save_refresh(
            "refresh-again", user_id=int(person.account_id), client_id="client-1",
            scopes=[], resource=None,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        await self.store.set_user_enabled(person.account_id, False)
        self.assertIsNone(await self.store.get_refresh("refresh-again"))


@unittest.skipUnless(VALKEY, "requires TEST_CLOUD_VALKEY_URL")
class CloudValkeyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from yougile_mcp.cloud.valkey import ValkeyCloudState
        self.state = await ValkeyCloudState.connect(
            VALKEY, namespace="test-" + os.urandom(8).hex() + ":",
        )

    async def asyncTearDown(self):
        await self.state.close()

    async def test_one_time_flow_revoke_and_login_failure_counter(self):
        flow = self.state.key("auth", "once")
        self.assertTrue(await self.state.put_json(flow, {"user": "one"}, ttl=30, once=True))
        self.assertFalse(await self.state.put_json(flow, {"user": "two"}, ttl=30, once=True))
        self.assertEqual((await self.state.take_json(flow))["user"], "one")
        self.assertIsNone(await self.state.take_json(flow))
        counter = self.state.key("failure", "ip")
        self.assertEqual(await self.state.count_failure(counter), 1)
        self.assertEqual(await self.state.count_failure(counter), 2)
        self.assertEqual(await self.state.failures(counter), 2)
        self.assertFalse(await self.state.is_revoked("issuer", "jti"))
        await self.state.revoke_access_jti("issuer", "jti", ttl=30)
        self.assertTrue(await self.state.is_revoked("issuer", "jti"))

    async def test_redis_shared_company_rate_budget(self):
        self.assertEqual(await self.state.acquire_company_slot("company-C", limit=2), 0)
        self.assertEqual(await self.state.acquire_company_slot("company-C", limit=2), 0)
        self.assertGreater(await self.state.acquire_company_slot("company-C", limit=2), 0)
