"""GEN-231 verified remote identity gate: revoke, audience and tenant isolation."""
from __future__ import annotations

import asyncio
import unittest
from dataclasses import replace

from yougile_mcp.mcp.remote_identity import AgentGrant, RemotePrincipalGate, VerifiedBearer

ISSUER = "https://idp.example.test/realm"
RESOURCE = "https://mcp.example.test/mcp"
COMPANY = "company-a"
READ = "yougile.boards.read"
WRITE = "yougile.boards.write"


class MemoryGrantRepository:
    def __init__(self):
        self.grants = {}
        self.revoked = set()
        self.fail = False
        self.calls = 0

    async def get_grant(self, *, issuer, subject, client_id):
        self.calls += 1
        if self.fail:
            raise OSError("DB unavailable with secret details")
        return self.grants.get((issuer, subject, client_id))

    async def is_token_revoked(self, *, issuer, token_id):
        if self.fail:
            raise OSError("revocation unavailable")
        return (issuer, token_id) in self.revoked


def bearer(subject="alice", client_id="client-1", token_id="token-1", **changes):
    token = VerifiedBearer(
        issuer=ISSUER, audiences=frozenset({RESOURCE}), subject=subject,
        client_id=client_id, token_id=token_id, not_before=1,
        expires_at=1000, scopes=frozenset({READ, WRITE}),
    )
    return replace(token, **changes)


def grant(subject="alice", client_id="client-1", **changes):
    value = AgentGrant(
        agent_id="actor-" + subject, issuer=ISSUER, subject=subject,
        client_id=client_id, company_id=COMPANY,
        scopes=frozenset({READ}), allowed_projects=frozenset({"project-1"}),
    )
    return replace(value, **changes)


class RemotePrincipalGateTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.repo = MemoryGrantRepository()
        value = grant()
        self.repo.grants[(value.issuer, value.subject, value.client_id)] = value
        self.gate = RemotePrincipalGate(
            expected_issuer=ISSUER, expected_audience=RESOURCE,
            company_id=COMPANY, repository=self.repo, clock=lambda: 100,
        )

    async def test_verified_agent_gets_only_intersection_of_rights(self):
        result = await self.gate.resolve(bearer())
        self.assertIsNotNone(result)
        self.assertEqual(result.subject, "actor-alice")
        self.assertEqual(result.scopes, frozenset({READ}))
        self.assertEqual(result.allowed_projects, frozenset({"project-1"}))
        self.assertFalse(result.company_wide)

    async def test_rejects_invalid_token_binding_without_storage_calls(self):
        invalids = [
            None,
            bearer(issuer="https://attacker.example.test/realm"),
            bearer(audiences=frozenset({"https://other.example.test/mcp"})),
            bearer(not_before=101),
            bearer(expires_at=100),
            bearer(not_before=1000, expires_at=999),
            bearer(subject=""),
            bearer(client_id=""),
            bearer(token_id=""),
            bearer(scopes=frozenset()),
            bearer(expires_at=True),
        ]
        for invalid in invalids:
            with self.subTest(invalid=invalid):
                before = self.repo.calls
                self.assertIsNone(await self.gate.resolve(invalid))
                self.assertEqual(before, self.repo.calls)

    async def test_revocation_applies_on_next_request(self):
        token = bearer()
        self.assertIsNotNone(await self.gate.resolve(token))
        self.repo.revoked.add((ISSUER, token.token_id))
        self.assertIsNone(await self.gate.resolve(token))

    async def test_removed_grant_and_wrong_company_denied(self):
        self.repo.grants.clear()
        self.assertIsNone(await self.gate.resolve(bearer()))
        self.repo.grants[(ISSUER, "alice", "client-1")] = grant(company_id="company-b")
        self.assertIsNone(await self.gate.resolve(bearer()))

    async def test_unknown_scope_not_granted_and_disabled_agent_denied(self):
        self.repo.grants[(ISSUER, "alice", "client-1")] = grant(
            scopes=frozenset({READ, "superadmin:anything"})
        )
        self.assertIsNone(await self.gate.resolve(bearer()))
        self.repo.grants[(ISSUER, "alice", "client-1")] = grant(enabled=False)
        self.assertIsNone(await self.gate.resolve(bearer()))

    async def test_token_cannot_impersonate_different_client(self):
        self.assertIsNone(await self.gate.resolve(bearer(client_id="unapproved-client")))
        self.assertIsNone(await self.gate.resolve(bearer(subject="mallory")))

    async def test_revocation_backend_outage_fails_closed(self):
        self.repo.fail = True
        self.assertIsNone(await self.gate.resolve(bearer()))

    async def test_no_project_grant_requires_explicit_company_wide(self):
        value = grant(allowed_projects=frozenset(), company_wide=False)
        self.repo.grants[(ISSUER, "alice", "client-1")] = value
        self.assertIsNone(await self.gate.resolve(bearer()))
        self.repo.grants[(ISSUER, "alice", "client-1")] = replace(
            value, company_wide=True
        )
        granted = await self.gate.resolve(bearer())
        self.assertTrue(granted.company_wide)

    async def test_two_agents_have_disjoint_grants_simultaneously(self):
        self.repo.grants[(ISSUER, "bob", "client-2")] = grant(
            subject="bob", client_id="client-2", scopes=frozenset({WRITE}),
            allowed_projects=frozenset({"project-2"}),
        )
        a, b = await asyncio.gather(
            self.gate.resolve(bearer()),
            self.gate.resolve(bearer(subject="bob", client_id="client-2", token_id="token-2")),
        )
        self.assertNotEqual(a.subject, b.subject)
        self.assertEqual(a.scopes, frozenset({READ}))
        self.assertEqual(b.scopes, frozenset({WRITE}))
        self.assertEqual(a.allowed_projects, frozenset({"project-1"}))
        self.assertEqual(b.allowed_projects, frozenset({"project-2"}))

    def test_rejects_unsafe_auth_settings_at_startup(self):
        for issuer, resource in (
            ("http://idp.example.test", RESOURCE),
            (ISSUER, "http://mcp.example.test/mcp"),
            ("https://user:secret@idp.example.test", RESOURCE),
            (ISSUER, ""),
        ):
            with self.subTest(issuer=issuer, resource=resource):
                with self.assertRaises(ValueError):
                    RemotePrincipalGate(
                        expected_issuer=issuer, expected_audience=resource,
                        company_id=COMPANY, repository=self.repo,
                    )


if __name__ == "__main__":
    unittest.main()
