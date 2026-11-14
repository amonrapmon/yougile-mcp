"""The single asynchronous client for the tested YouGile API slice."""

# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import asyncio
import math
import re
import threading
import time
from collections import deque
from collections.abc import Collection, Mapping
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, cast
from urllib.parse import quote

import httpx
from ..config import Settings
from .errors import (
    AuthenticationError,
    ApiError,
    InvalidInputError,
    MissingCompanyIdError,
    MissingCredentialsError,
    NotFoundError,
    PaginationError,
    PaginationLimitError,
    PermissionDeniedError,
    RateLimitError,
    RequestTimeoutError,
    UnsupportedOperationError,
    UncertainWriteError,
    UpstreamError,
    VendorValidationError,
)
from .models import (
    ApiResponse,
    BoardDto,
    BoardListDto,
    BoardSearchQuery,
    ColumnListDto,
    ColumnSearchQuery,
    CompanyCredentials,
    CompanyListDto,
    CompanySearchQuery,
    CreateColumnDto,
    FileUploadDto,
    TaskDto,
    TaskListDto,
    TaskSearchQuery,
    WithIdDto,
)
from .spec import Operation, operations, validate_schema

IMPLEMENTED_OPERATION_IDS = frozenset(
    {
        "getCompanies",
        "BoardController_search",
        "BoardController_get",
        "ColumnController_get",
        "ColumnController_search",
        "ColumnController_create",
        "AuthKeyController_search",
        "AuthKeyController_create",
        "AuthKeyController_delete",
        "UserController_create",
        "ChatMessageController_get",
        "ChatMessageController_search",
        "ChatMessageController_sendMessage",
        "ChatMessageController_typing",
        "ChatMessageController_update",
        "CrmContactPersonsController_create",
        "CrmExternalIdController_findContactByExternalId",
        "DepartmentController_create",
        "DepartmentController_get",
        "DepartmentController_search",
        "BoardController_create",
        "BoardController_update",
        "ColumnController_update",
        "GroupChatController_get",
        "GroupChatController_search",
        "GroupChatController_create",
        "GroupChatController_update",
        "ProjectController_create",
        "ProjectController_get",
        "ProjectController_search",
        "ProjectController_update",
        "ProjectRolesController_create",
        "ProjectRolesController_delete",
        "ProjectRolesController_get",
        "ProjectRolesController_search",
        "ProjectRolesController_update",
        "DepartmentController_update",
        "SprintStickerController_create",
        "SprintStickerController_getSticker",
        "SprintStickerController_search",
        "SprintStickerController_update",
        "SprintStickerStateController_create",
        "SprintStickerStateController_get",
        "SprintStickerStateController_update",
        "StringStickerController_create",
        "StringStickerController_get",
        "StringStickerController_search",
        "StringStickerController_update",
        "StringStickerStateController_create",
        "StringStickerStateController_get",
        "StringStickerStateController_update",
        "TaskController_create",
        "TaskController_update",
        "TaskController_updateChatSubscribers",
        "TaskController_search",
        "TaskController_searchReversed",
        "TaskController_get",
        "TaskController_getChatSubscribers",
        "TaskController_getLog",
        "UserController_get",
        "UserController_getMe",
        "UserController_search",
        "UserController_clearCustomStatus",
        "UserController_delete",
        "UserController_setCustomStatus",
        "UserController_update",
        "CompanyController_get",
        "CompanyController_update",
        "WebhookController_create",
        "WebhookController_put",
        "WebhookController_search",
        "FileController_uploadFile",
    }
)
_PAGE_SIZE_LIMIT = 1000
# shortcut: 100 pages, 10,000 items and 16 MiB per response, raise after payload and caller-budget review.
_PAGINATION_LIMITS = {"max_pages": 100, "max_items": 10_000}
_MAX_RESPONSE_BYTES = 16 * 1024 * 1024
_MAX_RETRY_AFTER_SECONDS = 5.0
_MAX_429_RETRIES = 2
_PATH_VARIABLE = re.compile(r"\{([^{}]+)\}")
_MEDIA_TYPE = re.compile(r"[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+")
_DEFAULT_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
_DEFAULT_UPLOAD_CONTENT_TYPES = frozenset({"text/plain"})
_RESERVED_HEADERS = {"authorization", "host", "content-length", "cookie", "content-type"}
_COMPANY_LIMITERS: dict[str, CompanyRateLimiter] = {}
_COMPANY_LIMITERS_LOCK = threading.Lock()


class CompanyRateLimiter:
    """Process-local rolling company budget shared by clients using this instance."""

    def __init__(
        self,
        *,
        clock: Any = time.monotonic,
        sleep: Any = asyncio.sleep,
    ) -> None:
        self._clock = clock
        self._sleep = sleep
        self._requests: deque[float] = deque()
        self._lock = threading.Lock()

    async def acquire(self) -> None:
        while True:
            with self._lock:
                now = self._clock()
                while self._requests and now - self._requests[0] >= 60:
                    self._requests.popleft()
                if len(self._requests) < 50:
                    self._requests.append(now)
                    return
                wait = max(0.0, 60 - (now - self._requests[0]))
            await self._sleep(wait)


def _company_limiter(settings: Settings, sleep: Any) -> CompanyRateLimiter:
    key = f"company:{settings.company_id}" if settings.company_id else "unconfigured"
    with _COMPANY_LIMITERS_LOCK:
        limiter = _COMPANY_LIMITERS.get(key)
        if limiter is None:
            limiter = CompanyRateLimiter(clock=time.monotonic, sleep=sleep)
            _COMPANY_LIMITERS[key] = limiter
        return limiter


class YouGileClient:
    """Clients with the same company ID share one process-local request budget."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        limiter: CompanyRateLimiter | None = None,
        sleep: Any = asyncio.sleep,
        timeout: float = 10.0,
        max_upload_bytes: int = _DEFAULT_MAX_UPLOAD_BYTES,
        allowed_upload_content_types: Collection[str] = _DEFAULT_UPLOAD_CONTENT_TYPES,
    ) -> None:
        if isinstance(max_upload_bytes, bool) or not isinstance(max_upload_bytes, int) or max_upload_bytes < 1:
            raise ValueError("max_upload_bytes must be a positive integer")
        try:
            upload_content_types = frozenset(item.strip().lower() for item in allowed_upload_content_types)
        except (AttributeError, TypeError):
            raise ValueError("allowed_upload_content_types must contain media types") from None
        if not upload_content_types or any(_MEDIA_TYPE.fullmatch(item) is None for item in upload_content_types):
            raise ValueError("allowed_upload_content_types must contain media types")
        self._api_key = settings.yougile_api_key.reveal() if settings.yougile_api_key else None
        self._company_id = settings.company_id
        self._limiter = limiter if limiter is not None else _company_limiter(settings, sleep)
        self._sleep = sleep
        self._max_upload_bytes = max_upload_bytes
        self._allowed_upload_content_types = upload_content_types
        self._http = httpx.AsyncClient(
            base_url=settings.yougile_base_url,
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        )

    async def __aenter__(self) -> YouGileClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def request(
        self,
        operation_id: str,
        *,
        path: Mapping[str, object] | None = None,
        query: Mapping[str, object] | None = None,
        body: object = None,
        headers: Mapping[str, str] | None = None,
        multipart_file: tuple[str, bytes, str] | None = None,
    ) -> ApiResponse[Any]:
        if operation_id not in IMPLEMENTED_OPERATION_IDS:
            raise UnsupportedOperationError()
        operation = operations()[operation_id]
        if operation.security and not self._company_id:
            raise MissingCompanyIdError()
        path_values = dict(path or {})
        query_values = dict(query or {})
        header_values = dict(headers or {})
        self._validate_parameters(operation, "path", path_values)
        self._validate_parameters(operation, "query", query_values)
        self._validate_parameters(operation, "header", header_values)
        url = self._build_path(operation, path_values)
        params = self._encode_query(query_values)
        files = None
        if operation_id == "FileController_uploadFile":
            if body is not None:
                raise InvalidInputError()
            filename, content, file_content_type = self._validate_upload_file(multipart_file)
            files = {"file": (filename, content, file_content_type)}
            request_body, content_type = None, None
        else:
            if multipart_file is not None:
                raise InvalidInputError()
            request_body, content_type = self._validate_body(operation, body)

        request_headers = {"Accept": "application/json, text/plain, text/html"}
        for key, value in header_values.items():
            if key.lower() in _RESERVED_HEADERS:
                raise InvalidInputError()
            request_headers[key] = value
        if operation.security:
            if not self._api_key:
                raise MissingCredentialsError()
            request_headers["Authorization"] = f"Bearer {self._api_key}"
        if content_type:
            request_headers["Content-Type"] = content_type

        return await self._send(operation, url, params, request_body, request_headers, files=files)

    async def upload_file(
        self,
        *,
        filename: str,
        content: bytes,
        content_type: str = "text/plain",
    ) -> ApiResponse[FileUploadDto]:
        return cast(
            ApiResponse[FileUploadDto],
            await self.request(
                "FileController_uploadFile",
                multipart_file=(filename, content, content_type),
            ),
        )

    async def search_boards(
        self, query: BoardSearchQuery | None = None
    ) -> ApiResponse[BoardListDto]:
        return cast(ApiResponse[BoardListDto], await self.request("BoardController_search", query=query))

    async def get_companies(
        self, credentials: CompanyCredentials, query: CompanySearchQuery | None = None
    ) -> ApiResponse[CompanyListDto]:
        return cast(
            ApiResponse[CompanyListDto],
            await self.request("getCompanies", query=query, body=credentials),
        )

    async def get_board(self, board_id: str) -> ApiResponse[BoardDto]:
        return cast(
            ApiResponse[BoardDto],
            await self.request("BoardController_get", path={"id": board_id}),
        )

    async def search_columns(
        self, query: ColumnSearchQuery | None = None
    ) -> ApiResponse[ColumnListDto]:
        return cast(ApiResponse[ColumnListDto], await self.request("ColumnController_search", query=query))

    async def search_tasks(
        self, query: TaskSearchQuery | None = None, *, reversed_order: bool = False
    ) -> ApiResponse[TaskListDto]:
        operation = "TaskController_searchReversed" if reversed_order else "TaskController_search"
        return cast(ApiResponse[TaskListDto], await self.request(operation, query=query))

    async def get_task(self, task_id: str) -> ApiResponse[TaskDto]:
        return cast(
            ApiResponse[TaskDto],
            await self.request("TaskController_get", path={"id": task_id}),
        )

    async def create_column(self, body: CreateColumnDto) -> ApiResponse[WithIdDto]:
        return cast(ApiResponse[WithIdDto], await self.request("ColumnController_create", body=body))

    async def list_all(
        self,
        operation_id: str,
        *,
        path: Mapping[str, object] | None = None,
        query: Mapping[str, object] | None = None,
        max_pages: int = _PAGINATION_LIMITS["max_pages"],
        max_items: int = _PAGINATION_LIMITS["max_items"],
    ) -> list[dict[str, Any]]:
        if max_pages < 1 or max_items < 1:
            raise InvalidInputError()
        operation = operations().get(operation_id)
        query_parameters = {
            parameter["name"]
            for parameter in operation.parameters
            if parameter.get("in") == "query"
        } if operation is not None else set()
        offset_pagination = {"limit", "offset"}.issubset(query_parameters)
        cursor_pagination = {"limit", "before"}.issubset(query_parameters)
        if operation_id not in IMPLEMENTED_OPERATION_IDS or not (
            offset_pagination or cursor_pagination
        ):
            raise UnsupportedOperationError()
        current_query = dict(query or {})
        page_size = current_query.get("limit", 50)
        if not isinstance(page_size, int) or isinstance(page_size, bool) or not 1 <= page_size <= _PAGE_SIZE_LIMIT:
            raise InvalidInputError()
        cursor_pagination = cursor_pagination and not offset_pagination
        if cursor_pagination:
            before_value = current_query.get("before")
            if before_value is not None and not _finite_number(before_value):
                raise InvalidInputError()
        else:
            offset_value = current_query.get("offset", 0)
            if not isinstance(offset_value, int) or isinstance(offset_value, bool) or offset_value < 0:
                raise InvalidInputError()

        items: list[dict[str, Any]] = []
        seen_offsets: set[int] = set()
        seen_cursors: set[int | float] = set()
        if cursor_pagination and before_value is not None:
            seen_cursors.add(before_value)
        for page_number in range(1, max_pages + 1):
            if cursor_pagination:
                if before_value is None:
                    current_query.pop("before", None)
                else:
                    current_query["before"] = before_value
            else:
                if offset_value in seen_offsets:
                    raise PaginationError()
                seen_offsets.add(offset_value)
                current_query["offset"] = offset_value
            response = await self.request(operation_id, path=path, query=current_query)
            data = response.data
            if not isinstance(data, dict):
                raise PaginationError()
            paging = data.get("paging")
            content = data.get("content")
            if not isinstance(paging, dict) or not isinstance(content, list):
                raise PaginationError()
            response_limit = _whole_number(paging.get("limit"))
            if response_limit < 1:
                raise PaginationError()
            if not cursor_pagination:
                response_offset = _whole_number(paging.get("offset"))
                if response_offset != offset_value:
                    raise PaginationError()
            if any(not isinstance(item, dict) for item in content):
                raise PaginationError()
            if len(items) + len(content) > max_items:
                raise PaginationLimitError()
            items.extend(cast(list[dict[str, Any]], content))
            if not paging.get("next"):
                return items
            if page_number == max_pages:
                raise PaginationLimitError()
            if cursor_pagination:
                if not content:
                    raise PaginationError()
                next_before = content[-1].get("timestamp")
                if not _finite_number(next_before):
                    raise PaginationError()
                if before_value is not None and next_before >= before_value:
                    raise PaginationError()
                if next_before in seen_cursors:
                    raise PaginationError()
                seen_cursors.add(next_before)
                before_value = next_before
            else:
                next_offset = response_offset + response_limit
                if next_offset <= response_offset or next_offset in seen_offsets:
                    raise PaginationError()
                offset_value = next_offset
        raise PaginationLimitError()

    async def _send(
        self,
        operation: Operation,
        url: str,
        params: list[tuple[str, str]],
        body: object,
        headers: dict[str, str],
        *,
        files: Mapping[str, tuple[str, bytes, str]] | None = None,
    ) -> ApiResponse[Any]:
        attempt = 0
        while True:
            await self._limiter.acquire()
            try:
                async with self._http.stream(
                    operation.method,
                    url,
                    params=params,
                    json=body if body is not None else None,
                    files=files,
                    headers=headers,
                ) as raw_response:
                    if raw_response.status_code == 429:
                        retry_after = _retry_after(raw_response.headers.get("Retry-After"))
                        if operation.effect == "read" and attempt < _MAX_429_RETRIES:
                            delay = retry_after if retry_after is not None else min(0.5 * (2**attempt), 5.0)
                            if delay <= _MAX_RETRY_AFTER_SECONDS:
                                attempt += 1
                                await self._sleep(delay)
                                continue
                        raise RateLimitError(status_code=429, retry_after=retry_after)
                    content = bytearray()
                    async for chunk in raw_response.aiter_bytes():
                        if len(content) + len(chunk) > _MAX_RESPONSE_BYTES:
                            raise UpstreamError(status_code=raw_response.status_code)
                        content.extend(chunk)
                    response = httpx.Response(
                        raw_response.status_code,
                        headers=raw_response.headers,
                        content=bytes(content),
                        request=raw_response.request,
                    )
            except httpx.TimeoutException:
                error = UncertainWriteError() if operation.effect != "read" else RequestTimeoutError()
                raise error from None
            except httpx.RequestError:
                error = UncertainWriteError() if operation.effect != "read" else UpstreamError()
                raise error from None

            if not 200 <= response.status_code < 300:
                raise _http_error(response.status_code)
            return _decode_response(operation, response)

    def _validate_parameters(
        self, operation: Operation, location: str, supplied: dict[str, object]
    ) -> None:
        declared = {
            item["name"]: item
            for item in operation.parameters
            if item.get("in") == location
        }
        if supplied.keys() - declared.keys():
            raise InvalidInputError()
        for name, parameter in declared.items():
            if parameter.get("required") and name not in supplied:
                raise InvalidInputError()
        for name, value in supplied.items():
            schema = declared[name].get("schema")
            if not isinstance(schema, dict):
                raise InvalidInputError()
            validate_schema(value, schema, request=True)

    def _validate_upload_file(
        self, multipart_file: tuple[str, bytes, str] | None
    ) -> tuple[str, bytes, str]:
        if not isinstance(multipart_file, tuple) or len(multipart_file) != 3:
            raise InvalidInputError()
        filename, content, content_type = multipart_file
        if (
            not isinstance(filename, str)
            or not filename
            or filename in {".", ".."}
            or any(character in filename for character in "/\\")
            or any(ord(character) < 32 or ord(character) == 127 for character in filename)
            or not isinstance(content, bytes)
            or len(content) > self._max_upload_bytes
            or not isinstance(content_type, str)
        ):
            raise InvalidInputError()
        normalized_type = content_type.strip().lower()
        if (
            _MEDIA_TYPE.fullmatch(normalized_type) is None
            or normalized_type not in self._allowed_upload_content_types
        ):
            raise InvalidInputError()
        return filename, content, normalized_type

    def _build_path(self, operation: Operation, path_values: dict[str, object]) -> str:
        names = set(_PATH_VARIABLE.findall(operation.path))
        if names != path_values.keys() or any(name.startswith("*") for name in names):
            raise InvalidInputError()
        return _PATH_VARIABLE.sub(
            lambda match: quote(str(path_values[match.group(1)]), safe=""), operation.path
        )

    def _encode_query(
        self, supplied: dict[str, object]
    ) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        for name, value in supplied.items():
            if name == "limit" and (not isinstance(value, int) or isinstance(value, bool) or value > _PAGE_SIZE_LIMIT):
                raise InvalidInputError()
            if isinstance(value, (list, tuple)):
                result.extend((name, _query_scalar(item)) for item in value)
            else:
                result.append((name, _query_scalar(value)))
        return result

    def _validate_body(self, operation: Operation, body: object) -> tuple[object, str | None]:
        request_body = operation.request_body
        if request_body is None:
            if body is not None:
                raise InvalidInputError()
            return None, None
        content = request_body.get("content", {})
        if "application/json" not in content:
            raise UnsupportedOperationError()
        if request_body.get("required") and body is None:
            raise InvalidInputError()
        if body is not None:
            try:
                validate_schema(body, content["application/json"].get("schema", {}), request=True)
            except InvalidInputError:
                raise
        return body, "application/json" if body is not None else None


def _query_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value)
    raise InvalidInputError()


def _whole_number(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
        raise PaginationError()
    return int(value)


def _finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


def _http_error(status_code: int) -> ApiError:
    if status_code == 401:
        return AuthenticationError(status_code=status_code)
    if status_code == 403:
        return PermissionDeniedError(status_code=status_code)
    if status_code == 404:
        return NotFoundError(status_code=status_code)
    if status_code in {400, 422}:
        return VendorValidationError(status_code=status_code)
    return UpstreamError(status_code=status_code)


def _decode_response(operation: Operation, response: httpx.Response) -> ApiResponse[Any]:
    content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if response.status_code == 204 or not response.content:
        body = None
    else:
        if content_type == "application/json" or content_type.endswith("+json"):
            try:
                body = response.json()
            except ValueError:
                raise UpstreamError(status_code=response.status_code) from None
        elif content_type.startswith("text/"):
            body = response.text
        else:
            raise UpstreamError(status_code=response.status_code)

    response_spec = operation.responses.get(str(response.status_code), operation.responses.get("default", {}))
    content = response_spec.get("content", {}) if isinstance(response_spec, dict) else {}
    schema = _response_schema(content, content_type)
    if body is not None:
        if schema is not None:
            validate_schema(body, schema, request=False)
    elif schema is not None:
        raise UpstreamError(status_code=response.status_code)
    return ApiResponse(status_code=response.status_code, data=body)


def _response_schema(content: object, content_type: str) -> object | None:
    if not isinstance(content, Mapping) or not content:
        return None
    actual_type = content_type.lower().split(";", 1)[0].strip()
    major_type = actual_type.partition("/")[0]
    for media_type in (actual_type, f"{major_type}/*", "*/*"):
        for declared_type, definition in content.items():
            if declared_type.lower() == media_type and isinstance(definition, Mapping):
                return definition.get("schema")
    raise UpstreamError()
