"""The single asynchronous client for the tested YouGile API slice."""

# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import asyncio
import re
import time
from collections import deque
from collections.abc import Mapping
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
        "ColumnController_search",
        "ColumnController_create",
        "TaskController_search",
        "TaskController_searchReversed",
        "TaskController_get",
    }
)
_PAGE_SIZE_LIMIT = 1000
# shortcut: 100 pages, 10,000 items and 16 MiB per response, raise after payload and caller-budget review.
_PAGINATION_LIMITS = {"max_pages": 100, "max_items": 10_000}
_MAX_RESPONSE_BYTES = 16 * 1024 * 1024
_MAX_RETRY_AFTER_SECONDS = 5.0
_MAX_429_RETRIES = 2
_PATH_VARIABLE = re.compile(r"\{([^{}]+)\}")
_RESERVED_HEADERS = {"authorization", "host", "content-length", "cookie"}


class CompanyRateLimiter:
    """A rolling company budget shared by every call using this instance."""

    def __init__(
        self,
        *,
        clock: Any = time.monotonic,
        sleep: Any = asyncio.sleep,
    ) -> None:
        self._clock = clock
        self._sleep = sleep
        self._requests: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = self._clock()
                while self._requests and now - self._requests[0] >= 60:
                    self._requests.popleft()
                if len(self._requests) < 50:
                    self._requests.append(now)
                    return
                wait = max(0.0, 60 - (now - self._requests[0]))
            await self._sleep(wait)


class YouGileClient:
    """One client per company; share it across actors and tools in that process."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        limiter: CompanyRateLimiter | None = None,
        sleep: Any = asyncio.sleep,
        timeout: float = 10.0,
    ) -> None:
        self._api_key = settings.yougile_api_key.reveal() if settings.yougile_api_key else None
        self._limiter = limiter or CompanyRateLimiter(sleep=sleep)
        self._sleep = sleep
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
    ) -> ApiResponse[Any]:
        if operation_id not in IMPLEMENTED_OPERATION_IDS:
            raise UnsupportedOperationError()
        operation = operations()[operation_id]
        path_values = dict(path or {})
        query_values = dict(query or {})
        header_values = dict(headers or {})
        self._validate_parameters(operation, "path", path_values)
        self._validate_parameters(operation, "query", query_values)
        self._validate_parameters(operation, "header", header_values)
        url = self._build_path(operation, path_values)
        params = self._encode_query(query_values)
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

        return await self._send(operation, url, params, request_body, request_headers)

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
        query: Mapping[str, object] | None = None,
        max_pages: int = _PAGINATION_LIMITS["max_pages"],
        max_items: int = _PAGINATION_LIMITS["max_items"],
    ) -> list[dict[str, Any]]:
        if max_pages < 1 or max_items < 1:
            raise InvalidInputError()
        if operation_id not in {
            "BoardController_search",
            "ColumnController_search",
            "TaskController_search",
            "TaskController_searchReversed",
        }:
            raise UnsupportedOperationError()
        current_query = dict(query or {})
        page_size = current_query.get("limit", 50)
        if not isinstance(page_size, int) or isinstance(page_size, bool) or not 1 <= page_size <= _PAGE_SIZE_LIMIT:
            raise InvalidInputError()
        offset_value = current_query.get("offset", 0)
        if not isinstance(offset_value, int) or isinstance(offset_value, bool) or offset_value < 0:
            raise InvalidInputError()

        items: list[dict[str, Any]] = []
        seen_offsets: set[int] = set()
        for page_number in range(1, max_pages + 1):
            if offset_value in seen_offsets:
                raise PaginationError()
            seen_offsets.add(offset_value)
            current_query["offset"] = offset_value
            response = await self.request(operation_id, query=current_query)
            data = response.data
            if not isinstance(data, dict):
                raise PaginationError()
            paging = data.get("paging")
            content = data.get("content")
            if not isinstance(paging, dict) or not isinstance(content, list):
                raise PaginationError()
            response_offset = _whole_number(paging.get("offset"))
            response_limit = _whole_number(paging.get("limit"))
            if response_offset != offset_value or response_limit < 1:
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
                    headers=headers,
                ) as raw_response:
                    if raw_response.status_code == 429:
                        retry_after = _retry_after(raw_response.headers.get("Retry-After"))
                        if operation.method == "GET" and attempt < _MAX_429_RETRIES:
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
                error = UncertainWriteError() if operation.method != "GET" else RequestTimeoutError()
                raise error from None
            except httpx.RequestError:
                error = UncertainWriteError() if operation.method != "GET" else UpstreamError()
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
    if response.status_code == 204 or not response.content:
        body = None
    else:
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
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
    if body is not None:
        schema = next(
            (media.get("schema") for media in content.values() if isinstance(media, dict) and "schema" in media),
            None,
        )
        if schema is not None:
            validate_schema(body, schema, request=False)
    elif any(isinstance(media, dict) and "schema" in media for media in content.values()):
        raise UpstreamError(status_code=response.status_code)
    return ApiResponse(status_code=response.status_code, data=body)
