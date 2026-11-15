"""Atomic Valkey state for OAuth and rate limits, independent of FastMCP.

Based on indalo-tech/yougile-mcp-cloud@ea88a0d5/kv.py,
© Indalo, AGPL-3.0-only. Uses redis.asyncio as a smaller adapter.
SPDX-License-Identifier: AGPL-3.0-only
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from .crypto import hash_token

_HIT = """
local n = redis.call('INCR', KEYS[1])
if redis.call('TTL', KEYS[1]) < 0 then
    redis.call('EXPIRE', KEYS[1], tonumber(ARGV[1]))
end
return n
"""

# Atomic shared company request budget; server TIME rather than host clocks.
_ACQUIRE = """
local key = KEYS[1]
local window = tonumber(ARGV[1])
local lim = tonumber(ARGV[2])
local tm = redis.call('TIME')
local now = tonumber(tm[1]) + tonumber(tm[2]) / 1000000
redis.call('ZREMRANGEBYSCORE', key, '-inf', now - window)
if redis.call('ZCARD', key) < lim then
    redis.call('ZADD', key, now, ARGV[3])
    redis.call('EXPIRE', key, math.ceil(window) + 1)
    return 0
end
local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
return tonumber(oldest[2]) + window - now + 0.05
"""


class ValkeyCloudState:
    """Short-lived authorization state. Never store raw passwords/API keys."""

    def __init__(self, client: Any, *, namespace: str = "ygcloud:"):
        if not namespace or ":" not in namespace:
            raise ValueError("Namespaced Valkey keys required")
        self.client = client
        self.namespace = namespace

    @classmethod
    async def connect(cls, url: str, *, namespace: str = "ygcloud:") -> "ValkeyCloudState":
        if not url.startswith(("redis://", "rediss://", "valkey://", "valkeys://")):
            raise ValueError("Invalid Valkey URL")
        from redis.asyncio import Redis

        normalized = url.replace("valkeys://", "rediss://", 1).replace("valkey://", "redis://", 1)
        client = Redis.from_url(normalized, decode_responses=False)
        await client.ping()
        return cls(client, namespace=namespace)

    def key(self, *segments: str) -> str:
        if not segments or any(not isinstance(s, str) or not s or ":" in s for s in segments):
            raise ValueError("Invalid scoped key")
        return self.namespace + ":".join(segments)

    async def close(self) -> None:
        await self.client.aclose()

    async def put_json(self, key: str, payload: Any, *, ttl: int, once: bool = False) -> bool:
        if not 1 <= ttl <= 24 * 60 * 60:
            raise ValueError("Invalid Valkey TTL")
        value = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return bool(await self.client.set(key, value, ex=ttl, nx=once))

    async def get_json(self, key: str) -> Any | None:
        raw = await self.client.get(key)
        return json.loads(raw) if raw else None

    async def take_json(self, key: str) -> Any | None:
        """GETDEL is atomic; flow/auth code cannot be consumed twice."""
        raw = await self.client.getdel(key)
        return json.loads(raw) if raw else None

    async def count_failure(self, key: str, *, window_seconds: int = 900) -> int:
        return int(await self.client.eval(_HIT, 1, key, window_seconds))

    async def failures(self, key: str) -> int:
        raw = await self.client.get(key)
        return int(raw or 0)

    async def revoke_access_jti(self, issuer: str, jti: str, *, ttl: int) -> None:
        if not issuer or not jti or ttl <= 0:
            raise ValueError("Invalid access token revocation")
        await self.client.set(
            self.key("revoked", hash_token(issuer), hash_token(jti)), b"1", ex=ttl,
        )

    async def is_revoked(self, issuer: str, jti: str) -> bool:
        return bool(await self.client.exists(
            self.key("revoked", hash_token(issuer), hash_token(jti))
        ))

    async def acquire_company_slot(
        self, company_id: str, *, limit: int = 45, window_seconds: int = 60,
    ) -> float:
        if not company_id or not 1 <= limit <= 50 or window_seconds <= 0:
            raise ValueError("Invalid vendor rate-limit policy")
        result = await self.client.eval(
            _ACQUIRE, 1,
            self.key("company-budget", hash_token(company_id)),
            window_seconds, limit, uuid.uuid4().hex,
        )
        return max(0.0, float(result))
