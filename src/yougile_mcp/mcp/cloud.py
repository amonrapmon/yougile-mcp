"""Per-request, per-YouGile-account bridge for a future hosted OAuth shell.

The hosted shell authenticates the MCP request and returns an opaque *verified*
account identifier. Only a trusted account repository supplies company and API
credentials. Tool arguments and bearer claims cannot select another company.

This module neither processes passwords nor opens a network endpoint.
Adaptation target: indalo-tech/yougile-mcp-cloud (AGPL-3.0-only).
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from typing import Any, Protocol

import httpx
from mcp.server import Server, ServerRequestContext
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
    ToolAnnotations,
)

from ..api import YouGileClient
from ..config import Secret, Settings
from .dispatch import InvocationPrincipal, ToolDispatcher, ToolDispatchError
from .factory import ToolRegistry, build_registry
from .ownership import CompanyIdentityVerifier, ProjectOwnershipResolver
from .runtime import _visible


@dataclass(frozen=True)
class VerifiedCloudActor:
    """Internal user ID from the upstream *verified* OAuth access token."""
    account_id: str


@dataclass(frozen=True)
class CloudAccount:
    """Trusted DB record for the account, not an OAuth claim or user input."""
    company_id: str
    api_key: Secret
    enabled: bool = True


class CloudAccountRepository(Protocol):
    """Must look up the current DB record, including bans and key rotation."""

    async def load(self, account_id: str) -> CloudAccount | None: ...


CloudActorResolver = Callable[
    [ServerRequestContext], Awaitable[VerifiedCloudActor | None]
]


class CloudAccessDenied(Exception):
    """Generic denial without leaking account identifiers or secret details."""


@dataclass
class CloudTenant:
    principal: InvocationPrincipal
    dispatcher: ToolDispatcher


class CloudTenantSessions:
    """Bind one verified OAuth user to one provider-issued, company-scoped key.

    Every MCP request rechecks the current account store. HTTP and OAuth live
    outside this class; the host must use a cryptographically verified token
    to construct VerifiedCloudActor. No global/fallback YouGile key is allowed.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        resolve_actor: CloudActorResolver,
        accounts: CloudAccountRepository,
        registry: ToolRegistry | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        if settings.company_id is not None or settings.has_api_key:
            raise ValueError("Hosted bridge cannot use the process-wide YouGile key")
        if not callable(resolve_actor) or accounts is None:
            raise ValueError("An authenticated OAuth actor and account store are required")
        self.settings = settings
        self.resolve_actor = resolve_actor
        self.accounts = accounts
        self.registry = registry if registry is not None else build_registry()
        self.transport = transport
        self._scopes = frozenset(
            {desc.scope for desc in self.registry.list()}
            | {"yougile." + desc.domain + ".destructive" for desc in self.registry.list()}
        )

    @asynccontextmanager
    async def open(self, context: ServerRequestContext) -> AsyncIterator[CloudTenant]:
        try:
            actor = await self.resolve_actor(context)
            if (
                not isinstance(actor, VerifiedCloudActor)
                or not actor.account_id
                or len(actor.account_id) > 128
            ):
                raise CloudAccessDenied()
            account = await self.accounts.load(actor.account_id)
            if (
                not isinstance(account, CloudAccount)
                or account.enabled is not True
                or not account.company_id
                or not isinstance(account.api_key, Secret)
                or not account.api_key.reveal()
            ):
                raise CloudAccessDenied()
        except Exception:
            # DB or OAuth adapter failures must not become anonymous access.
            raise CloudAccessDenied() from None

        settings = replace(
            self.settings,
            company_id=account.company_id,
            yougile_api_key=account.api_key,
        )
        principal = InvocationPrincipal(
            subject=actor.account_id,
            company_id=account.company_id,
            scopes=self._scopes,
            allowed_projects=frozenset(),
            company_wide=True,  # Full Access within the user's own YouGile key.
        )
        async with YouGileClient(settings, transport=self.transport) as client:
            dispatcher = ToolDispatcher(
                client,
                company_id=account.company_id,
                registry=self.registry,
                company_verifier=CompanyIdentityVerifier(
                    client, company_id=account.company_id,
                ),
                project_resolver=ProjectOwnershipResolver(
                    client, company_id=account.company_id,
                ),
            )
            yield CloudTenant(principal, dispatcher)


def _failure(category: str) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps({"category": category}))],
        is_error=True,
    )


def make_cloud_mcp_server(sessions: CloudTenantSessions) -> Server:
    """MCP SDK server with authenticated principal *and* dispatcher per call.

    Neither the tool list nor the tool-call dispatcher is shared between
    different provider users. No HTTP listener is created by this function.
    """

    async def list_tools(
        context: ServerRequestContext, params: PaginatedRequestParams | None,
    ) -> ListToolsResult:
        try:
            async with sessions.open(context) as tenant:
                tools = [
                    Tool(
                        name=item.name,
                        description=item.description,
                        input_schema=item.input_schema,
                        output_schema=item.output_schema,
                        annotations=ToolAnnotations(
                            read_only_hint=item.access == "read",
                            destructive_hint=(
                                item.access in {"admin", "destructive"}
                                or item.requires_approval
                            ),
                            idempotent_hint=item.method == "GET",
                            open_world_hint=True,
                        ),
                    )
                    for item in tenant.dispatcher.registry.list()
                    if _visible(tenant.principal, item, tenant.dispatcher)
                ]
                return ListToolsResult(tools=tools)
        except CloudAccessDenied:
            return ListToolsResult(tools=[])
        except Exception:
            # Avoid exposing account records or backend exceptions through MCP.
            return ListToolsResult(tools=[])

    async def call_tool(
        context: ServerRequestContext, params: CallToolRequestParams,
    ) -> CallToolResult:
        try:
            async with sessions.open(context) as tenant:
                try:
                    result = await tenant.dispatcher.call(
                        params.name, params.arguments or {}, tenant.principal,
                    )
                except ToolDispatchError as exc:
                    error: dict[str, Any] = {"category": exc.category}
                    if exc.status_code is not None:
                        error["status_code"] = exc.status_code
                    return CallToolResult(
                        content=[TextContent(type="text", text=json.dumps(error))],
                        is_error=True,
                    )
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text", text=json.dumps(result, ensure_ascii=False),
                        )
                    ],
                    structured_content=result,
                )
        except CloudAccessDenied:
            return _failure("permission_denied")
        except Exception:
            return _failure("internal_error")

    return Server(
        "YouGile MCP Cloud",
        version="0.0.1",
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )
