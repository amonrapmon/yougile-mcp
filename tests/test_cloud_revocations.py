"""Regression tests for durable retired YouGile key revocation.

These use disposable PostgreSQL from CI, never the user's cloud database.
"""
from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import patch

from yougile_mcp.cloud.crypto import CloudCipher, new_encryption_key
from yougile_mcp.cloud.persistence import PostgresCloudStore
from yougile_mcp.cloud.revocations import process_one_key_revocation
from yougile_mcp.cloud.yougile_signin import CloudSignInError, ProvisionedYouGileAccount
from yougile_mcp.config import Secret

DATABASE = os.environ.get("TEST_CLOUD_DATABASE_URL")


def person(key: str) -> ProvisionedYouGileAccount:
    return ProvisionedYouGileAccount(
        company_id="company-A", user_id="person-1",
        email="p@example.test", name="Test",
        is_admin=False, api_key=Secret(key),
    )


@unittest.skipUnless(DATABASE, "requires disposable PostgreSQL")
class DurableKeyRevocationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = PostgresCloudStore(DATABASE, CloudCipher([new_encryption_key()]))
        await self.store.open()
        await self.store.migrate()
        async with self.store.pool.connection() as conn:
            await conn.execute(
                "TRUNCATE cloud_vendor_key_revocations, cloud_refresh_tokens,"
                "cloud_oauth_clients, cloud_users, cloud_companies,"
                "cloud_audit_log RESTART IDENTITY CASCADE"
            )
        await self.store.save_account(person("vendor-key-before"), company_name="Alpha")
        await self.store.save_account(person("vendor-key-after"), company_name="Alpha")

    async def asyncTearDown(self):
        await self.store.close()

    async def test_retry_persisted_then_success_removes_job(self):
        class SometimesUnavailable:
            def __init__(self):
                self.used = []

            async def revoke_key(self, key):
                self.used.append(key)
                if len(self.used) == 1:
                    raise CloudSignInError("fake provider temporarily unavailable")

        signin = SometimesUnavailable()
        with self.assertLogs("uvicorn.error", level="INFO") as logs:
            self.assertTrue(await process_one_key_revocation(self.store, signin))
        self.assertEqual(signin.used, ["vendor-key-before"])
        self.assertIn("stage=old_key_revoke_started", "\n".join(logs.output))
        self.assertIn("stage=retry_scheduled", "\n".join(logs.output))
        self.assertNotIn("vendor-key-before", "\n".join(logs.output))
        self.assertFalse(await process_one_key_revocation(self.store, signin))
        async with self.store.pool.connection() as conn:
            row = await (await conn.execute(
                "SELECT attempts,lease_token,ready_at > now() AS delayed "
                "FROM cloud_vendor_key_revocations"
            )).fetchone()
            self.assertEqual(row["attempts"], 1)
            self.assertIsNone(row["lease_token"])
            self.assertTrue(row["delayed"])
            audit = await (await conn.execute(
                "SELECT event FROM cloud_audit_log "
                "WHERE event='old_vendor_key_revocation_failed'"
            )).fetchone()
            self.assertIsNotNone(audit)
            # Advance the clock by making the queued job immediately eligible.
            await conn.execute(
                "UPDATE cloud_vendor_key_revocations SET ready_at=now()"
            )
        with self.assertLogs("uvicorn.error", level="INFO") as logs2:
            self.assertTrue(await process_one_key_revocation(self.store, signin))
        self.assertEqual(signin.used, ["vendor-key-before", "vendor-key-before"])
        self.assertIn("stage=old_key_revoke_finished", "\n".join(logs2.output))
        self.assertFalse(await process_one_key_revocation(self.store, signin))
        async with self.store.pool.connection() as conn:
            row = await (await conn.execute(
                "SELECT count(*) AS n FROM cloud_vendor_key_revocations"
            )).fetchone()
        self.assertEqual(row["n"], 0)

    async def test_hanging_vendor_revoke_is_bounded_and_retried(self):
        class Hangs:
            async def revoke_key(self, _key):
                await asyncio.Event().wait()

        with patch("yougile_mcp.cloud.revocations._REVOKE_TIMEOUT", 0.02):
            self.assertTrue(await asyncio.wait_for(
                process_one_key_revocation(self.store, Hangs()), timeout=1,
            ))
        async with self.store.pool.connection() as conn:
            row = await (await conn.execute(
                "SELECT attempts, lease_token FROM cloud_vendor_key_revocations"
            )).fetchone()
        self.assertEqual(row["attempts"], 1)
        self.assertIsNone(row["lease_token"])

    async def test_parallel_claim_cannot_take_one_job_twice(self):
        claimed = await asyncio.gather(
            self.store.claim_key_revocation(), self.store.claim_key_revocation(),
        )
        self.assertEqual(sum(job is not None for job in claimed), 1)
        job = next(job for job in claimed if job is not None)
        self.assertTrue(await self.store.complete_key_revocation(job))
        self.assertIsNone(await self.store.claim_key_revocation())


if __name__ == "__main__":
    unittest.main()
