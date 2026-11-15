"""Official Python MCP SDK v2 adapter over the 72-operation registry.

No transport listener or user-controlled principal construction here. The host
must provide an authenticated principal resolver for every SDK request.
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

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

from .dispatch import InvocationPrincipal, ToolDispatchError, ToolDispatcher
from .factory import ToolDescriptor

IdentityResolver = Callable[[ServerRequestContext], Awaitable[InvocationPrincipal | None]]


def _visible(principal: InvocationPrincipal | None, descriptor: ToolDescriptor,
             dispatcher: ToolDispatcher) -> bool:
    if (
        principal is None or not principal.subject or
        principal.company_id != dispatcher.company_id or
        descriptor.scope not in principal.scopes
    ):
        return False
    if descriptor.resource_scope == "company":
        return principal.company_wide
    return bool(principal.allowed_projects) and dispatcher.project_resolver is not None


def make_mcp_server(
    dispatcher: ToolDispatcher,
    *,
    resolve_principal: IdentityResolver,
) -> Server:
    """Register every tool through two SDK-native handlers.

    Identity resolution must be trusted middleware injected by the host. Do
    not call this with a client-selected principal in any remote deployment.
    """
    if not callable(resolve_principal):
        raise ValueError("A trusted per-request identity resolver is required")

    async def list_tools(
        context: ServerRequestContext, params: PaginatedRequestParams | None
    ) -> ListToolsResult:
        principal = await resolve_principal(context)
        return ListToolsResult(tools=[
            Tool(
                name=item.name,
                description=item.description,
                input_schema=item.input_schema,
                output_schema=item.output_schema,
                annotations=ToolAnnotations(
                    read_only_hint=item.access == "read",
                    destructive_hint=(
                        item.access in {"admin", "destructive"} or item.requires_approval
                    ),
                    idempotent_hint=item.method == "GET",
                    open_world_hint=True,
                ),
            )
            for item in dispatcher.registry.list()
            if _visible(principal, item, dispatcher)
        ])

    async def call_tool(
        context: ServerRequestContext, params: CallToolRequestParams
    ) -> CallToolResult:
        principal = await resolve_principal(context)
        try:
            result = await dispatcher.call(params.name, params.arguments or {}, principal)
        except ToolDispatchError as exc:
            # Only normalized categories leave the server; never send original
            # YouGile messages or values from the payload.
            error = {"category": exc.category}
            if exc.status_code is not None:
                error["status_code"] = exc.status_code
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(error))],
                is_error=True,
            )
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False))],
            structured_content=result,
        )

    return Server(
        "YouGile MCP",
        version="0.0.1",
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )
