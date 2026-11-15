"""Explicitly scoped, local-only stdio MCP host.

The trusted owner of the local child process provisions one identity file per
agent. stdio carries no bearer credentials and never opens a network port.
Remote clients require a separately reviewed OAuth identity integration.
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import json
import os
import re
import stat
from typing import Any

from mcp.server.stdio import stdio_server

from ..api import YouGileClient
from ..config import ConfigError, Settings
from .dispatch import InvocationPrincipal, ToolDispatcher
from .factory import ToolRegistry, build_registry
from .ownership import CompanyIdentityVerifier, ProjectOwnershipResolver
from .runtime import make_mcp_server

_MAX_IDENTITY_BYTES = 16 * 1024
_SUBJECT = re.compile(r"[A-Za-z0-9_.:/@-]{1,128}")
_FIELDS = frozenset({"subject", "company_id", "scopes", "allowed_projects", "company_wide"})


def _unique_str_list(value: Any) -> frozenset[str]:
    if (
        not isinstance(value, list)
        or len(value) != len(set(item for item in value if isinstance(item, str)))
        or any(not isinstance(item, str) or not item or len(item) > 128 for item in value)
    ):
        raise ConfigError("Invalid local identity grants")
    return frozenset(value)


def load_identity(
    path: str | None, *, company_id: str, registry: ToolRegistry | None = None
) -> InvocationPrincipal:
    """Load a private OS-owned per-agent identity from an absolute, non-symlink file.

    This is the trust boundary of a LOCAL stdio subprocess, not an alternative
    to authentication for remote HTTP. Reject unsafe permissions/ownership.
    """
    if not path or not os.path.isabs(path):
        raise ConfigError("MCP_STDIO_IDENTITY_FILE must be an absolute path")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    fd = None
    try:
        fd = os.open(path, flags)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > _MAX_IDENTITY_BYTES:
            raise ConfigError("Identity file must be a small regular file")
        if os.name == "posix":
            if info.st_mode & 0o077:
                raise ConfigError("Identity file must have owner-only permissions")
            if info.st_uid != os.getuid():
                raise ConfigError("Identity file must belong to the process owner")
        raw = os.read(fd, _MAX_IDENTITY_BYTES + 1)
        if len(raw) > _MAX_IDENTITY_BYTES:
            raise ConfigError("Identity file exceeds maximum size")
    except OSError:
        raise ConfigError("Unable to securely read MCP_STDIO_IDENTITY_FILE") from None
    finally:
        if fd is not None:
            os.close(fd)

    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ConfigError("Invalid local identity file") from None
    if not isinstance(document, dict) or set(document) != _FIELDS:
        raise ConfigError("Incomplete local identity")
    subject = document["subject"]
    if not isinstance(subject, str) or _SUBJECT.fullmatch(subject) is None:
        raise ConfigError("Invalid local agent identity")
    if document["company_id"] != company_id or not company_id:
        raise ConfigError("Configured company and agent identity do not match")
    scopes = _unique_str_list(document["scopes"])
    projects = _unique_str_list(document["allowed_projects"])
    wide = document["company_wide"]
    if not isinstance(wide, bool):
        raise ConfigError("company_wide must be a boolean")
    if not wide and not projects:
        raise ConfigError("Identity requires a company or project grant")
    known = {tool.scope for tool in (registry or build_registry()).list()}
    known |= {
        "yougile." + tool.domain + ".destructive"
        for tool in (registry or build_registry()).list()
    }
    if not scopes or not scopes.issubset(known):
        raise ConfigError("Identity contains unknown or missing operation scopes")
    return InvocationPrincipal(
        subject=subject, company_id=company_id, scopes=scopes,
        allowed_projects=projects, company_wide=wide,
    )


async def serve_stdio(settings: Settings, principal: InvocationPrincipal) -> None:
    """Run the official SDK over stdio with a single explicitly configured actor."""
    if (
        settings.transport != "stdio"
        or settings.company_id is None
        or not settings.has_api_key
        or settings.company_id != principal.company_id
    ):
        raise ConfigError("Local stdio server requires company-bound credentials")
    async with YouGileClient(settings) as client:
        dispatcher = ToolDispatcher(
            client,
            company_id=settings.company_id,
            registry=build_registry(),
            company_verifier=CompanyIdentityVerifier(client, company_id=settings.company_id),
            project_resolver=ProjectOwnershipResolver(client, company_id=settings.company_id),
        )

        async def resolve_principal(_: Any) -> InvocationPrincipal:
            # The host is one OS-launched child process for one trusted agent.
            # Never parse principal, scopes or company ID from an MCP message.
            return principal

        server = make_mcp_server(dispatcher, resolve_principal=resolve_principal)
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream, write_stream, server.create_initialization_options(),
            )
