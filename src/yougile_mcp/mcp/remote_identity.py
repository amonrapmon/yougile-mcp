"""Fail-closed authorization gate for *already verified* remote bearer identities.

This module does not parse JWTs, sign tokens or open an HTTP listener.
The upstream official SDK TokenVerifier / verified IdP adapter must establish
signature authenticity before constructing VerifiedBearer. A tenant-owned grant
store remains the authority for agent grants, never the caller's MCP arguments.
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from ..config import is_https_service_url
from .dispatch import InvocationPrincipal
from .factory import ToolRegistry, build_registry


@dataclass(frozen=True)
class VerifiedBearer:
    """Claims emitted by a trusted signature/introspection verifier, not a decoder.

    An HTTP adapter must NOT create this from unverified client JSON/JWT claims.
    """
    issuer: str
    audiences: frozenset[str]
    subject: str
    client_id: str
    token_id: str
    not_before: int
    expires_at: int
    scopes: frozenset[str]


@dataclass(frozen=True)
class AgentGrant:
    """Server-managed ACL entry, bound to issuer, subject and OAuth client."""
    agent_id: str
    issuer: str
    subject: str
    client_id: str
    company_id: str
    scopes: frozenset[str]
    allowed_projects: frozenset[str]
    company_wide: bool = False
    enabled: bool = True


class GrantRepository(Protocol):
    """Authoritative persisted grant data; evaluated on every request."""

    async def get_grant(
        self, *, issuer: str, subject: str, client_id: str
    ) -> AgentGrant | None: ...

    async def is_token_revoked(self, *, issuer: str, token_id: str) -> bool: ...


class RemotePrincipalGate:
    """Translate a verified bearer into the existing policy principal.

    Both token privileges AND the current server-side grant must allow a
    scope. A DB error, stale token, revoked token, changed client or company
    mismatch results in denial. This class intentionally cannot expose HTTP.
    """

    def __init__(
        self, *,
        expected_issuer: str,
        expected_audience: str,
        company_id: str,
        repository: GrantRepository,
        registry: ToolRegistry | None = None,
        clock: object = time.time,
    ):
        if not is_https_service_url(expected_issuer):
            raise ValueError("Expected issuer must be a trusted HTTPS URL")
        if not is_https_service_url(expected_audience):
            raise ValueError("Expected audience must be a trusted HTTPS resource URL")
        if not company_id:
            raise ValueError("Company binding is required")
        if repository is None:
            raise ValueError("A durable grant repository is required")
        self.expected_issuer = expected_issuer
        self.expected_audience = expected_audience
        self.company_id = company_id
        self.repository = repository
        self.registry = registry or build_registry()
        self.clock = clock
        self._known_scopes = frozenset(
            {tool.scope for tool in self.registry.list()}
            | {"yougile." + tool.domain + ".destructive" for tool in self.registry.list()}
        )

    async def resolve(self, verified: VerifiedBearer | None) -> InvocationPrincipal | None:
        if not isinstance(verified, VerifiedBearer):
            return None
        try:
            now = int(self.clock())
            if (
                verified.issuer != self.expected_issuer
                or self.expected_audience not in verified.audiences
                or not verified.subject
                or not verified.client_id
                or not verified.token_id
                or not isinstance(verified.not_before, int)
                or isinstance(verified.not_before, bool)
                or not isinstance(verified.expires_at, int)
                or isinstance(verified.expires_at, bool)
                or verified.not_before > now
                or verified.expires_at <= now
                or verified.expires_at <= verified.not_before
                or not isinstance(verified.scopes, frozenset)
                or not verified.scopes
            ):
                return None
            if await self.repository.is_token_revoked(
                issuer=verified.issuer, token_id=verified.token_id,
            ):
                return None
            grant = await self.repository.get_grant(
                issuer=verified.issuer, subject=verified.subject,
                client_id=verified.client_id,
            )
            if (
                not isinstance(grant, AgentGrant)
                or not grant.enabled
                or grant.issuer != verified.issuer
                or grant.subject != verified.subject
                or grant.client_id != verified.client_id
                or grant.company_id != self.company_id
                or not grant.agent_id
                or not isinstance(grant.company_wide, bool)
                or not isinstance(grant.scopes, frozenset)
                or not grant.scopes.issubset(self._known_scopes)
                or not isinstance(grant.allowed_projects, frozenset)
                or (not grant.company_wide and not grant.allowed_projects)
            ):
                return None
            scopes = verified.scopes & grant.scopes & self._known_scopes
            if not scopes:
                return None
            return InvocationPrincipal(
                subject=grant.agent_id,
                company_id=grant.company_id,
                scopes=frozenset(scopes),
                allowed_projects=grant.allowed_projects,
                company_wide=grant.company_wide,
            )
        except Exception:
            # Revocation, grant-storage, or verification dependencies cannot
            # be allowed to fail open. Never propagate raw identity details.
            return None
