"""Minimal fail-closed policy model; NOT yet wired to an MCP transport.

SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    subject: str
    scopes: frozenset[str]
    allowed_domains: frozenset[str]


def authorize(principal: Principal | None, domain: str, access: str) -> bool:
    if principal is None or not principal.subject:
        return False
    if domain not in principal.allowed_domains:
        return False
    if access not in {"read", "write", "write_destructive", "admin"}:
        return False
    return f"yougile.{domain}.{access}" in principal.scopes
