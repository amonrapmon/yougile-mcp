"""Tenant-aware PostgreSQL store for hosted YouGile identities and OAuth state.

Schema modeled on indalo-tech/yougile-mcp-cloud@ea88a0d5/db.py,
© Indalo, AGPL-3.0-only. The schema intentionally has no billing or
trial state. ORM-less transactional SQL; credential bytes are encrypted.
SPDX-License-Identifier: AGPL-3.0-only
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from importlib.resources import files
from typing import Any, Mapping

from ..mcp.cloud import CloudAccount
from ..config import Secret
from .yougile_signin import ProvisionedYouGileAccount
from .crypto import CloudCipher, hash_token


@dataclass(frozen=True)
class SavedAccount:
    account_id: str
    previous_api_key: Secret | None  # Old credential, to revoke after commit.


class PostgresCloudStore:
    """Requires psycopg[binary,pool]; it is optional for local stdio users.

    Production supplies a real pool; tests can inject an in-process or service
    pool. A user is scoped by BOTH vendor company and YouGile user ID.
    """

    def __init__(self, dsn: str, cipher: CloudCipher, *, pool: Any = None):
        if not isinstance(cipher, CloudCipher):
            raise ValueError("An initialized cloud cipher is required")
        if pool is None and not dsn:
            raise ValueError("PostgreSQL connection string required")
        self._dsn = dsn
        self._cipher = cipher
        self.pool = pool
        self._owns_pool = pool is None

    async def open(self) -> None:
        if self.pool is None:
            from psycopg_pool import AsyncConnectionPool
            from psycopg.rows import dict_row

            self.pool = AsyncConnectionPool(
                self._dsn,
                open=False,
                min_size=1,
                max_size=10,
                kwargs={"row_factory": dict_row, "autocommit": True},
            )
            await self.pool.open(wait=True)

    async def close(self) -> None:
        if self._owns_pool and self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def migrate(self) -> None:
        if self.pool is None:
            raise RuntimeError("Cloud store is not open")
        migration = files("yougile_mcp.cloud.migrations").joinpath("001_cloud.sql").read_text(
            encoding="utf-8"
        )
        async with self.pool.connection() as conn:
            async with conn.transaction():
                await conn.execute("SELECT pg_advisory_xact_lock(2317272)")
                await conn.execute(
                    "CREATE TABLE IF NOT EXISTS cloud_schema_migrations "
                    "(name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
                )
                cur = await conn.execute(
                    "SELECT name FROM cloud_schema_migrations WHERE name = %s",
                    ("001_cloud.sql",),
                )
                if await cur.fetchone() is None:
                    await conn.execute(migration)
                    await conn.execute(
                        "INSERT INTO cloud_schema_migrations (name) VALUES (%s)",
                        ("001_cloud.sql",),
                    )

    async def save_account(
        self, person: ProvisionedYouGileAccount, *, company_name: str,
    ) -> SavedAccount:
        """Atomic company/user upsert; returns old key for post-commit revoke.

        A concurrent first sign-in of the same vendor user is serialized by
        a transaction-scoped advisory lock. Caller must revoke newly created
        key if this transaction fails.
        """
        if not person.company_id or not person.user_id or not company_name:
            raise ValueError("Complete YouGile identity required")
        ciphertext = self._cipher.encrypt(person.api_key)
        async with self.pool.connection() as conn, conn.transaction():
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtext(%s))",
                (person.company_id + ":" + person.user_id,),
            )
            await conn.execute(
                "INSERT INTO cloud_companies (id,name) VALUES (%s,%s) "
                "ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, updated_at=now()",
                (person.company_id, company_name),
            )
            old_cur = await conn.execute(
                "SELECT api_key_enc FROM cloud_users "
                "WHERE company_id=%s AND yougile_user_id=%s FOR UPDATE",
                (person.company_id, person.user_id),
            )
            old = await old_cur.fetchone()
            # Decrypt before committing so a missing rotation key cannot
            # orphan the new stored vendor credential after a successful commit.
            previous = self._cipher.decrypt(old["api_key_enc"]) if old else None
            cur = await conn.execute(
                """
                INSERT INTO cloud_users
                    (company_id,yougile_user_id,email,name,is_admin,api_key_enc)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (company_id,yougile_user_id) DO UPDATE SET
                    email=EXCLUDED.email, name=EXCLUDED.name,
                    is_admin=EXCLUDED.is_admin,
                    api_key_enc=EXCLUDED.api_key_enc,
                    updated_at=now()
                RETURNING id
                """,
                (person.company_id, person.user_id, person.email, person.name,
                 person.is_admin, ciphertext),
            )
            new = await cur.fetchone()
        return SavedAccount(str(new["id"]), previous)

    async def load(self, account_id: str) -> CloudAccount | None:
        """Authoritative lookup for CloudTenantSessions; check BOTH enabled flags."""
        if not isinstance(account_id, str) or not account_id.isascii() or (
            not account_id.isdecimal() or len(account_id) > 18
        ):
            return None
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "SELECT u.company_id, u.api_key_enc, u.enabled AS user_enabled, "
                "c.enabled AS company_enabled FROM cloud_users u "
                "JOIN cloud_companies c ON c.id = u.company_id WHERE u.id=%s",
                (int(account_id),),
            )
            row = await cur.fetchone()
        if not row or not row["user_enabled"] or not row["company_enabled"]:
            return None
        return CloudAccount(
            company_id=row["company_id"], api_key=self._cipher.decrypt(row["api_key_enc"]),
        )

    async def get_user(self, account_id: str) -> dict[str, Any] | None:
        if not str(account_id).isascii() or not str(account_id).isdecimal():
            return None
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "SELECT id,company_id,yougile_user_id,email,name,is_admin,enabled "
                "FROM cloud_users WHERE id=%s", (int(account_id),),
            )
            return await cur.fetchone()

    async def set_user_enabled(self, account_id: str, enabled: bool) -> None:
        if not str(account_id).isascii() or not str(account_id).isdecimal():
            raise ValueError("Invalid account id")
        async with self.pool.connection() as conn, conn.transaction():
            await conn.execute(
                "UPDATE cloud_users SET enabled=%s,updated_at=now() WHERE id=%s",
                (enabled, int(account_id)),
            )
            if not enabled:
                await conn.execute(
                    "DELETE FROM cloud_refresh_tokens WHERE user_id=%s",
                    (int(account_id),),
                )

    async def set_company_enabled(self, company_id: str, enabled: bool) -> None:
        if not company_id:
            raise ValueError("Company required")
        async with self.pool.connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    "UPDATE cloud_companies SET enabled=%s,updated_at=now() WHERE id=%s",
                    (enabled, company_id),
                )
                if not enabled:
                    await conn.execute(
                        "DELETE FROM cloud_refresh_tokens WHERE user_id IN "
                        "(SELECT id FROM cloud_users WHERE company_id=%s)",
                        (company_id,),
                    )

    async def save_oauth_client(self, client_id: str, info: Mapping[str, Any]) -> None:
        from psycopg.types.json import Jsonb

        async with self.pool.connection() as conn:
            await conn.execute(
                "INSERT INTO cloud_oauth_clients (client_id,info) VALUES (%s,%s) "
                "ON CONFLICT (client_id) DO UPDATE SET info=EXCLUDED.info",
                (client_id, Jsonb(dict(info))),
            )

    async def get_oauth_client(self, client_id: str) -> dict[str, Any] | None:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "SELECT info FROM cloud_oauth_clients WHERE client_id=%s", (client_id,),
            )
            row = await cur.fetchone()
        return row["info"] if row else None

    async def save_refresh(
        self, opaque_token: str, *, user_id: int, client_id: str,
        scopes: list[str], resource: str | None, expires_at: datetime,
    ) -> None:
        from psycopg.types.json import Jsonb

        async with self.pool.connection() as conn:
            await conn.execute(
                "INSERT INTO cloud_refresh_tokens "
                "(token_hash,user_id,client_id,scopes,resource,expires_at) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (hash_token(opaque_token), user_id, client_id,
                 Jsonb(scopes), resource, expires_at),
            )

    async def get_refresh(self, opaque_token: str) -> dict[str, Any] | None:
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "SELECT * FROM cloud_refresh_tokens WHERE token_hash=%s",
                (hash_token(opaque_token),),
            )
            return await cur.fetchone()

    async def take_refresh(self, opaque_token: str) -> dict[str, Any] | None:
        """Atomic consume; replay of a refresh token is impossible."""
        async with self.pool.connection() as conn:
            cur = await conn.execute(
                "DELETE FROM cloud_refresh_tokens WHERE token_hash=%s RETURNING *",
                (hash_token(opaque_token),),
            )
            return await cur.fetchone()

    async def revoke_user_refresh(self, user_id: int) -> None:
        async with self.pool.connection() as conn:
            await conn.execute(
                "DELETE FROM cloud_refresh_tokens WHERE user_id=%s", (user_id,),
            )

    async def audit(
        self, event: str, *, company_id: str | None = None,
        user_id: int | None = None, detail: Mapping[str, Any] | None = None,
    ) -> None:
        from psycopg.types.json import Jsonb

        # Never accept arbitrary payloads containing credentials as audit detail.
        allowed = {"operation", "outcome", "client_id"}
        payload = {
            k: v for k, v in (detail or {}).items()
            if k in allowed and isinstance(v, str) and len(v) < 256
        }
        async with self.pool.connection() as conn:
            await conn.execute(
                "INSERT INTO cloud_audit_log (event,company_id,user_id,detail) "
                "VALUES (%s,%s,%s,%s)",
                (event, company_id, user_id, Jsonb(payload)),
            )
