"""Company and project ownership checks via the existing verified YouGile API client.

Only object lineages represented in the compatible OAS can be authorized as
project scoped. Unknown/ambiguous resources are denied, never guessed.
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Mapping
from typing import Any

from ..api import ApiError, YouGileClient
from .dispatch import InvocationPrincipal
from .factory import ToolDescriptor


class CompanyIdentityVerifier:
    """Bind the configured API credential to the provider's actual company ID.

    The provider lookup is cached briefly per immutable client/credential
    instance to avoid exhausting YouGile rate limits. Create a fresh verifier
    when rotating keys. Any mismatch or API failure denies the invocation.
    """

    def __init__(
        self, client: YouGileClient, *, company_id: str,
        ttl_seconds: float = 30, clock: Callable[[], float] = time.monotonic,
    ):
        if not company_id or getattr(client, "_company_id", None) != company_id:
            raise ValueError("Mismatched company-bound YouGile client")
        if ttl_seconds <= 0 or ttl_seconds > 60:
            raise ValueError("Company verification TTL must be between 0 and 60 seconds")
        self.client = client
        self.company_id = company_id
        self.ttl_seconds = ttl_seconds
        self.clock = clock
        self._verified_until = 0.0
        self._lock = asyncio.Lock()

    async def __call__(self, principal: InvocationPrincipal) -> bool:
        if principal.company_id != self.company_id:
            return False
        async with self._lock:
            if self.clock() < self._verified_until:
                return True
            try:
                response = await self.client.request("CompanyController_get")
            except ApiError:
                return False
            if not isinstance(response.data, Mapping):
                return False
            if response.data.get("id") != self.company_id:
                return False
            self._verified_until = self.clock() + self.ttl_seconds
            return True


class ProjectOwnershipResolver:
    """Resolve project from authoritative vendor object hierarchy.

    Direct: projectId, /projects/{id}, or immutable object detail -> parent.
    Indirect: task -> column -> board -> project; column -> board -> project.
    For moves, both source and destination projects must be authorized.
    Company-global stickers/chats are intentionally never project-filtered:
    the compatible OpenAPI exposes no provable project ownership for them.
    """

    def __init__(self, client: YouGileClient, *, company_id: str):
        if not company_id or getattr(client, "_company_id", None) != company_id:
            raise ValueError("Mismatched company-bound YouGile client")
        self.client = client
        self.company_id = company_id

    async def __call__(
        self, principal: InvocationPrincipal, descriptor: ToolDescriptor,
        arguments: Mapping[str, Any],
    ) -> str:
        if principal.company_id != self.company_id or not principal.allowed_projects:
            return ""
        path = arguments.get("path")
        body = arguments.get("body")
        if not isinstance(path, Mapping):
            path = {}
        if not isinstance(body, Mapping):
            body = {}
        operation_id = descriptor.operation_id
        family, sep, action = operation_id.partition("Controller_")
        if not sep:
            return ""
        try:
            if family == "Project":
                source = _identifier(path.get("id"))
                destinations = set()
            elif family == "ProjectRoles":
                source = _identifier(path.get("projectId"))
                destinations = set()
            elif family == "Board":
                source = await self._board_project(path["id"]) if "id" in path else (
                    _identifier(body.get("projectId")) if action == "create" else ""
                )
                destinations = {_identifier(body["projectId"])} if "projectId" in body else set()
            elif family == "Column":
                source = await self._column_project(path["id"]) if "id" in path else (
                    await self._board_project(body["boardId"]) if action == "create" and
                    "boardId" in body else ""
                )
                destinations = {
                    await self._board_project(body["boardId"])
                } if "boardId" in body else set()
            elif family == "Task":
                source = await self._task_project(path["id"]) if "id" in path else (
                    await self._column_project(body["columnId"])
                    if action == "create" and "columnId" in body else ""
                )
                destinations = {
                    await self._column_project(body["columnId"])
                } if "columnId" in body else set()
            else:
                return ""
            all_projects = {source, *destinations}
            if not source or not all_projects.issubset(principal.allowed_projects):
                return ""
            return source
        except (ApiError, KeyError, TypeError, ValueError):
            # A denied lookup is deliberately indistinguishable from a resource
            # in another company/project. Never disclose vendor error detail.
            return ""

    async def _board_project(self, board_id: Any) -> str:
        response = await self.client.request("BoardController_get", path={"id": _identifier(board_id)})
        return _identifier(response.data["projectId"])

    async def _column_project(self, column_id: Any) -> str:
        response = await self.client.request("ColumnController_get", path={"id": _identifier(column_id)})
        return await self._board_project(response.data["boardId"])

    async def _task_project(self, task_id: Any) -> str:
        response = await self.client.request("TaskController_get", path={"id": _identifier(task_id)})
        return await self._column_project(response.data["columnId"])


def _identifier(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Missing resource identifier")
    return value
