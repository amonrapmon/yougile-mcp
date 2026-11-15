"""Protocol-neutral, fail-closed execution of registered YouGile operations.

Authenticated principal, resource verification and approval services are supplied by
the host. Without them, calls are denied: this module exposes no public transport.
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import threading
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Mapping, Protocol

from jsonschema import Draft202012Validator, ValidationError

from ..api import ApiError, YouGileClient
from .factory import ToolDescriptor, ToolRegistry, build_registry

_MAX_OUTPUT_BYTES = 256 * 1024
_MAX_FILE_BYTES = 2 * 1024 * 1024
_SECRET_FIELDS = frozenset({"companyId", "authorization", "apiKey", "password", "token"})


@dataclass(frozen=True)
class InvocationPrincipal:
    """Claims constructed by a trusted identity adapter, never by tool arguments."""

    subject: str
    company_id: str
    scopes: frozenset[str]
    allowed_projects: frozenset[str]
    company_wide: bool = False


class ToolDispatchError(Exception):
    """Sanitized failure category; no request body, secrets or vendor text."""

    def __init__(self, category: str, *, status_code: int | None = None):
        super().__init__(category)
        self.category = category
        self.status_code = status_code


class ResourceResolver(Protocol):
    """Verify resource ownership with trusted company-bound data, not caller claims."""

    async def __call__(
        self, principal: InvocationPrincipal, descriptor: ToolDescriptor,
        arguments: Mapping[str, Any],
    ) -> str: ...


class SecretResolver(Protocol):
    """Get protected request fields from a server vault, never MCP input."""

    async def __call__(
        self, principal: InvocationPrincipal, operation_id: str
    ) -> Mapping[str, Any]: ...


AuditSink = Callable[[Mapping[str, str]], None]
CompanyVerifier = Callable[[InvocationPrincipal], Awaitable[bool]]


def _payload_fingerprint(
    principal: InvocationPrincipal, tool: ToolDescriptor, args: Mapping[str, Any]
) -> str:
    payload = {
        "actor": principal.subject,
        "company": principal.company_id,
        "operation": tool.operation_id,
        "args": args,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class OneTimeApprovals:
    """Local trusted approval ledger for testing/single-process flows, not remote auth.

    grant() must only be invoked by a separately authenticated owner workflow.
    A remote multi-replica deployment needs shared durable approval state.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._grants: dict[str, float] = {}
        self._lock = threading.Lock()

    def grant(
        self, principal: InvocationPrincipal, descriptor: ToolDescriptor,
        arguments: Mapping[str, Any], *, ttl_seconds: float = 60,
    ) -> None:
        if ttl_seconds <= 0 or ttl_seconds > 300:
            raise ValueError("Invalid approval lifetime")
        fingerprint = _payload_fingerprint(principal, descriptor, arguments)
        with self._lock:
            self._grants[fingerprint] = self._clock() + ttl_seconds

    def consume(
        self, principal: InvocationPrincipal, descriptor: ToolDescriptor,
        arguments: Mapping[str, Any],
    ) -> bool:
        fingerprint = _payload_fingerprint(principal, descriptor, arguments)
        with self._lock:
            expires = self._grants.pop(fingerprint, None)
            return expires is not None and self._clock() < expires


class ToolDispatcher:
    def __init__(
        self,
        client: YouGileClient,
        *,
        company_id: str,
        registry: ToolRegistry | None = None,
        project_resolver: ResourceResolver | None = None,
        company_verifier: CompanyVerifier | None = None,
        secret_resolver: SecretResolver | None = None,
        approvals: OneTimeApprovals | None = None,
        audit: AuditSink | None = None,
    ):
        if not company_id or getattr(client, "_company_id", None) != company_id:
            raise ValueError("Client must be bound to the same trusted company")
        self.client = client
        self.company_id = company_id
        self.registry = registry if registry is not None else build_registry()
        self.project_resolver = project_resolver
        self.company_verifier = company_verifier
        self.secret_resolver = secret_resolver
        self.approvals = approvals
        self.audit = audit

    def _record(self, principal: InvocationPrincipal | None, tool: ToolDescriptor, outcome: str) -> None:
        if self.audit is not None:
            self.audit({
                "actor": principal.subject if principal else "anonymous",
                "company": self.company_id,
                "operation": tool.operation_id,
                "outcome": outcome,
            })

    async def call(
        self, name: str, arguments: Mapping[str, Any] | None,
        principal: InvocationPrincipal | None,
    ) -> dict[str, Any]:
        try:
            tool = self.registry.get(name)
        except KeyError:
            raise ToolDispatchError("unknown_tool") from None
        try:
            result = await self._call_checked(tool, arguments, principal)
        except ToolDispatchError as exc:
            self._record(principal, tool, exc.category)
            raise
        except ApiError as exc:
            self._record(principal, tool, exc.category)
            raise ToolDispatchError(exc.category, status_code=exc.status_code) from None
        except Exception:
            self._record(principal, tool, "internal_error")
            raise ToolDispatchError("internal_error") from None
        self._record(principal, tool, "success")
        return result

    async def _call_checked(
        self, tool: ToolDescriptor, arguments: Mapping[str, Any] | None,
        principal: InvocationPrincipal | None,
    ) -> dict[str, Any]:
        if principal is None or not principal.subject or principal.company_id != self.company_id:
            raise ToolDispatchError("permission_denied")
        if tool.scope not in principal.scopes:
            raise ToolDispatchError("permission_denied")
        if not isinstance(arguments, Mapping):
            raise ToolDispatchError("invalid_input")
        supplied = dict(arguments)
        try:
            Draft202012Validator(tool.input_schema).validate(supplied)
        except ValidationError:
            raise ToolDispatchError("invalid_input") from None
        if _has_sensitive_fields(supplied):
            raise ToolDispatchError("invalid_input")
        if tool.resource_scope == "company" and not principal.company_wide:
            raise ToolDispatchError("permission_denied")
        if self.company_verifier is not None and not await self.company_verifier(principal):
            raise ToolDispatchError("permission_denied")
        if tool.resource_scope == "project":
            if self.project_resolver is None:
                raise ToolDispatchError("permission_denied")
            project_id = await self.project_resolver(principal, tool, supplied)
            if not project_id or (
                not principal.company_wide and project_id not in principal.allowed_projects
            ):
                raise ToolDispatchError("permission_denied")
        body = supplied.get("body")
        elevated_delete = isinstance(body, dict) and "deleted" in body
        if elevated_delete and "yougile." + tool.domain + ".destructive" not in principal.scopes:
            raise ToolDispatchError("permission_denied")
        if tool.requires_approval or elevated_delete:
            if self.approvals is None or not self.approvals.consume(principal, tool, supplied):
                raise ToolDispatchError("approval_required")
        path = supplied.get("path")
        query = supplied.get("query")
        multipart_file = None
        if tool.credentials:
            if self.secret_resolver is None:
                raise ToolDispatchError("credentials_unavailable")
            injected = await self.secret_resolver(principal, tool.operation_id)
            if set(injected) - {"path", "body"}:
                raise ToolDispatchError("credentials_unavailable")
            path = injected.get("path", path)
            body = injected.get("body", body)
            if not isinstance(path, (Mapping, type(None))):
                raise ToolDispatchError("credentials_unavailable")
            if tool.operation_id == "AuthKeyController_delete" and (
                not path or set(path) != {"key"}
            ):
                raise ToolDispatchError("credentials_unavailable")
            if isinstance(body, Mapping) and body.get("companyId", principal.company_id) != principal.company_id:
                raise ToolDispatchError("credentials_unavailable")
        if tool.multipart:
            upload = supplied["multipart_file"]
            try:
                data = base64.b64decode(upload["content_base64"], validate=True)
            except (binascii.Error, ValueError):
                raise ToolDispatchError("invalid_input") from None
            if not data or len(data) > _MAX_FILE_BYTES:
                raise ToolDispatchError("invalid_input")
            multipart_file = (upload["filename"], data, upload["content_type"])
        response = await self.client.request(
            tool.operation_id, path=path, query=query, body=body,
            multipart_file=multipart_file,
        )
        data = {"redacted": True} if tool.redacted_result else response.data
        result = {"status_code": response.status_code, "data": data}
        try:
            Draft202012Validator(tool.output_schema).validate(result)
        except ValidationError:
            raise ToolDispatchError("upstream_failure") from None
        serialized = json.dumps(result, separators=(",", ":"), ensure_ascii=False)
        if len(serialized.encode("utf-8")) > _MAX_OUTPUT_BYTES:
            raise ToolDispatchError("result_too_large")
        return result


def _has_sensitive_fields(value: Any) -> bool:
    if isinstance(value, Mapping):
        if any(key in _SECRET_FIELDS for key in value):
            return True
        return any(_has_sensitive_fields(child) for child in value.values())
    if isinstance(value, list):
        return any(_has_sensitive_fields(child) for child in value)
    return False
