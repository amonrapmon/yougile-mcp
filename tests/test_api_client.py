"""Fake-transport contract tests for the shared YouGile API core."""

from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx

from yougile_mcp.api import (
    AuthenticationError,
    CompanyRateLimiter,
    InvalidInputError,
    MissingCredentialsError,
    NotFoundError,
    PaginationError,
    PaginationLimitError,
    PermissionDeniedError,
    RateLimitError,
    RequestTimeoutError,
    UncertainWriteError,
    UpstreamError,
    VendorValidationError,
    YouGileClient,
)
from yougile_mcp.api.client import _decode_response
from yougile_mcp.api.spec import Operation
from yougile_mcp.config import Settings


ROOT = Path(__file__).resolve().parents[1]
SECRET = "test-secret-do-not-log"


def _settings(api_key: str | None = SECRET) -> Settings:
    values = {} if api_key is None else {"YOUGILE_API_KEY": api_key}
    return Settings.from_env(values)


def _page(offset: int, rows: list[dict[str, Any]], *, next_page: bool, limit: int = 50) -> dict:
    return {
        "paging": {"count": len(rows), "limit": limit, "offset": offset, "next": next_page},
        "content": rows,
    }


def _board(board_id: str = "board-1") -> dict[str, str]:
    return {"id": board_id, "title": "Board", "projectId": "project-1"}


def _task(task_id: str = "task-1") -> dict[str, Any]:
    return {"id": task_id, "title": "Task", "timestamp": 123}


async def _no_sleep(_: float) -> None:
    return None


class ApiClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_headers_query_and_response_dto(self):
        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json=_page(3, [_board()], next_page=False))

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            response = await client.search_boards(
                {"includeDeleted": True, "limit": 50, "offset": 3, "title": "R&D board"}
            )

        request = seen[0]
        self.assertEqual(request.method, "GET")
        self.assertEqual(request.url.path, "/api-v2/boards")
        self.assertEqual(request.headers["Authorization"], f"Bearer {SECRET}")
        self.assertEqual(request.url.params["title"], "R&D board")
        self.assertEqual(request.url.params["includeDeleted"], "true")
        self.assertEqual(response.data["content"][0]["projectId"], "project-1")

    async def test_company_lookup_keeps_credentials_in_body_without_bearer(self):
        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(
                200,
                json=_page(0, [{"id": "company-1", "name": "Company", "isAdmin": True}], next_page=False),
            )

        async with YouGileClient(
            _settings(None), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            result = await client.get_companies(
                {"login": "user@example.test", "password": SECRET, "name": "Workspace"},
                {"limit": 50, "offset": 0},
            )

        request = seen[0]
        self.assertEqual(request.url.path, "/api-v2/auth/companies")
        self.assertNotIn("Authorization", request.headers)
        self.assertEqual(request.url.params["offset"], "0")
        self.assertEqual(json.loads(request.content)["password"], SECRET)
        self.assertEqual(result.data["content"][0]["isAdmin"], True)

    async def test_company_lookup_rejects_missing_credentials(self):
        calls = 0

        def handler(_: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(200, json=_page(0, [], next_page=False))

        async with YouGileClient(
            _settings(None), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            with self.assertRaises(InvalidInputError):
                await client.get_companies({"login": "user@example.test"})  # type: ignore[typeddict-item]
        self.assertEqual(calls, 0)

    async def test_path_value_is_percent_encoded(self):
        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json=_task("id/part? a"))

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            await client.get_task("id/part? a")

        self.assertEqual(seen[0].url.raw_path, b"/api-v2/tasks/id%2Fpart%3F%20a")

    async def test_board_detail_and_column_list_schemas(self):
        responses = [
            httpx.Response(200, json=_board()),
            httpx.Response(200, json=_page(0, [{"id": "column-1", "title": "To do", "boardId": "board-1"}], next_page=False)),
        ]

        def handler(_: httpx.Request) -> httpx.Response:
            return responses.pop(0)

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            board = await client.get_board("board-1")
            columns = await client.search_columns({"boardId": "board-1"})

        self.assertEqual(board.data["projectId"], "project-1")
        self.assertEqual(columns.data["content"][0]["boardId"], "board-1")

    async def test_optional_query_fields_are_omitted_and_unknown_fields_rejected(self):
        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json=_page(0, [], next_page=False))

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            await client.search_boards({"title": "only this"})
            with self.assertRaises(InvalidInputError):
                await client.search_boards({"invented": "field"})  # type: ignore[typeddict-item]

        self.assertEqual(dict(seen[0].url.params), {"title": "only this"})
        self.assertEqual(len(seen), 1)

    async def test_task_search_maps_both_confirmed_list_operations(self):
        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append((request.method, request.url.path))
            return httpx.Response(200, json=_page(0, [_task()], next_page=False))

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            await client.search_tasks({"columnId": "column-1"})
            await client.search_tasks({"columnId": "column-1"}, reversed_order=True)

        self.assertEqual(seen, [("GET", "/api-v2/task-list"), ("GET", "/api-v2/tasks")])

    async def test_missing_required_path_and_body_fields_fail_before_http(self):
        calls = 0

        def handler(_: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(201, json={"id": "column-1"})

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            with self.assertRaises(InvalidInputError):
                await client.request("BoardController_get")
            with self.assertRaises(InvalidInputError):
                await client.create_column({"title": "Missing board"})  # type: ignore[typeddict-item]

        self.assertEqual(calls, 0)

    async def test_write_sends_json_body_and_returns_created_dto(self):
        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(201, json={"id": "column-1"})

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            result = await client.create_column(
                {"title": "To do", "boardId": "board-1", "idempotencyKey": "key-1"}
            )

        request = seen[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.url.path, "/api-v2/columns")
        self.assertEqual(request.headers["Content-Type"], "application/json")
        self.assertEqual(json.loads(request.content), {
            "title": "To do", "boardId": "board-1", "idempotencyKey": "key-1"
        })
        self.assertEqual(result.data, {"id": "column-1"})

    async def test_missing_api_key_fails_before_http(self):
        calls = 0

        def handler(_: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(200, json=_page(0, [], next_page=False))

        async with YouGileClient(
            _settings(None), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            with self.assertRaises(MissingCredentialsError):
                await client.search_boards()
        self.assertEqual(calls, 0)

    async def test_secrets_do_not_appear_in_reprs_or_normalized_errors(self):
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(403, text=f"vendor echoed {SECRET}")

        settings = _settings()
        client = YouGileClient(
            settings, transport=httpx.MockTransport(handler), sleep=_no_sleep
        )
        try:
            self.assertNotIn(SECRET, repr(settings))
            self.assertNotIn(SECRET, repr(client))
            with self.assertRaises(PermissionDeniedError) as raised:
                await client.search_boards()
            self.assertNotIn(SECRET, str(raised.exception))
            self.assertNotIn(SECRET, repr(raised.exception))
        finally:
            await client.aclose()

    async def test_status_mapping_does_not_expose_error_body(self):
        cases = {
            400: VendorValidationError,
            401: AuthenticationError,
            403: PermissionDeniedError,
            404: NotFoundError,
            422: VendorValidationError,
            500: UpstreamError,
            503: UpstreamError,
        }
        for status, error_type in cases.items():
            with self.subTest(status=status):
                def handler(_: httpx.Request, status: int = status) -> httpx.Response:
                    return httpx.Response(status, text=f"private body {SECRET}")

                async with YouGileClient(
                    _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
                ) as client:
                    with self.assertRaises(error_type) as raised:
                        await client.search_boards()
                self.assertEqual(raised.exception.status_code, status)
                self.assertNotIn(SECRET, str(raised.exception))

    async def test_429_retry_after_is_bounded_and_get_retry_is_safe(self):
        calls = 0
        sleeps = []

        async def capture_sleep(delay: float) -> None:
            sleeps.append(delay)

        def retry_handler(_: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                return httpx.Response(429, headers={"Retry-After": "0"})
            return httpx.Response(200, json=_page(0, [], next_page=False))

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(retry_handler), sleep=capture_sleep
        ) as client:
            response = await client.search_boards()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls, 2)
        self.assertEqual(sleeps, [0.0])

        calls = 0

        def long_wait_handler(_: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(429, headers={"Retry-After": "30"})

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(long_wait_handler), sleep=capture_sleep
        ) as client:
            with self.assertRaises(RateLimitError) as raised:
                await client.search_boards()
        self.assertEqual(calls, 1)
        self.assertEqual(raised.exception.retry_after, 30.0)

        calls = 0

        def write_limited_handler(_: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(429, headers={"Retry-After": "0"})

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(write_limited_handler), sleep=capture_sleep
        ) as client:
            with self.assertRaises(RateLimitError):
                await client.create_column({"title": "To do", "boardId": "board-1"})
        self.assertEqual(calls, 1)

    async def test_post_timeout_is_uncertain_and_never_retried(self):
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            raise httpx.ReadTimeout(f"timeout {SECRET}", request=request)

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            with self.assertRaises(UncertainWriteError) as raised:
                await client.create_column({"title": "To do", "boardId": "board-1"})
        self.assertEqual(calls, 1)
        self.assertNotIn(SECRET, str(raised.exception))

    async def test_get_timeout_has_timeout_category(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timeout", request=request)

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            with self.assertRaises(RequestTimeoutError):
                await client.search_boards()

    async def test_cancellation_is_preserved(self):
        started = asyncio.Event()
        release = asyncio.Event()

        class BlockingTransport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
                started.set()
                await release.wait()
                return httpx.Response(200, json=_page(0, [], next_page=False))

        async with YouGileClient(
            _settings(), transport=BlockingTransport(), sleep=_no_sleep
        ) as client:
            task = asyncio.create_task(client.search_boards())
            await started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

    async def test_redirect_is_not_followed(self):
        calls = 0

        def handler(_: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(302, headers={"Location": "https://attacker.example/"})

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            with self.assertRaises(UpstreamError):
                await client.search_boards()
        self.assertEqual(calls, 1)

    async def test_200_201_202_204_and_empty_body_responses(self):
        outcomes = [
            httpx.Response(200, json=_page(0, [], next_page=False)),
            httpx.Response(201, json={"id": "column-1"}),
            httpx.Response(202, json={"accepted": True}),
            httpx.Response(204),
        ]

        def handler(_: httpx.Request) -> httpx.Response:
            return outcomes.pop(0)

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            self.assertEqual((await client.search_boards()).status_code, 200)
            self.assertEqual((await client.create_column({"title": "x", "boardId": "b"})).status_code, 201)
            accepted = await client.create_column({"title": "x", "boardId": "b"})
            empty = await client.create_column({"title": "x", "boardId": "b"})
        self.assertEqual(accepted.data, {"accepted": True})
        self.assertEqual(empty.status_code, 204)
        self.assertIsNone(empty.data)

    async def test_invalid_json_and_response_dto_are_upstream_errors(self):
        responses = [
            httpx.Response(200, headers={"Content-Type": "application/json"}, content=b"bad-json"),
            httpx.Response(200, json={"id": "missing-required-title-and-project"}),
        ]

        def handler(_: httpx.Request) -> httpx.Response:
            return responses.pop(0)

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            with self.assertRaises(UpstreamError):
                await client.search_boards()
            with self.assertRaises(UpstreamError):
                await client.get_board("board-1")

    async def test_empty_success_response_is_rejected_when_dto_is_declared(self):
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200)

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            with self.assertRaises(UpstreamError):
                await client.search_boards()

    async def test_response_body_is_size_bounded(self):
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"123456")

        with patch("yougile_mcp.api.client._MAX_RESPONSE_BYTES", 5):
            async with YouGileClient(
                _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
            ) as client:
                with self.assertRaises(UpstreamError):
                    await client.search_boards()

    async def test_html_text_response_decoding(self):
        operation = Operation(
            operation_id="text",
            method="GET",
            path="/text",
            parameters=(),
            request_body=None,
            responses={"200": {"content": {"text/html": {"schema": {"type": "string"}}}}},
            security=(),
        )
        result = _decode_response(
            operation,
            httpx.Response(200, headers={"Content-Type": "text/html"}, content=b"<p>ok</p>"),
        )
        self.assertEqual(result.data, "<p>ok</p>")

    async def test_pagination_handles_empty_single_and_multiple_pages(self):
        for pages, expected_count in (
            ([_page(0, [], next_page=False)], 0),
            ([_page(0, [_board()], next_page=False)], 1),
            ([_page(0, [_board("a")], next_page=True), _page(50, [_board("b")], next_page=False)], 2),
        ):
            responses = list(pages)

            def handler(_: httpx.Request) -> httpx.Response:
                return httpx.Response(200, json=responses.pop(0))

            async with YouGileClient(
                _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
            ) as client:
                items = await client.list_all("BoardController_search")
            self.assertEqual(len(items), expected_count)

    async def test_pagination_rejects_duplicate_offsets_and_unbounded_results(self):
        calls = 0

        def repeated_offset(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            requested = int(request.url.params.get("offset", "0"))
            reported = 0 if requested else 0
            return httpx.Response(200, json=_page(reported, [_board()], next_page=True))

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(repeated_offset), sleep=_no_sleep
        ) as client:
            with self.assertRaises(PaginationError):
                await client.list_all("BoardController_search")
        self.assertEqual(calls, 2)

        def too_many(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_page(0, [_board(), _board("b")], next_page=False))

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(too_many), sleep=_no_sleep
        ) as client:
            with self.assertRaises(PaginationLimitError):
                await client.list_all("BoardController_search", max_items=1)

    async def test_pagination_page_budget_and_vendor_page_size_are_bounded(self):
        def more_pages(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_page(0, [_board()], next_page=True))

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(more_pages), sleep=_no_sleep
        ) as client:
            with self.assertRaises(PaginationLimitError):
                await client.list_all("BoardController_search", max_pages=1)
            with self.assertRaises(InvalidInputError):
                await client.list_all("BoardController_search", query={"limit": 1001})

    async def test_shared_company_rate_limiter_honors_fifty_per_minute(self):
        now = [0.0]
        delays = []

        async def advance(seconds: float) -> None:
            delays.append(seconds)
            now[0] += seconds

        limiter = CompanyRateLimiter(clock=lambda: now[0], sleep=advance)
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_page(0, [], next_page=False))

        transport_one = httpx.MockTransport(handler)
        transport_two = httpx.MockTransport(handler)
        async with YouGileClient(
            _settings(), transport=transport_one, limiter=limiter, sleep=advance
        ) as first, YouGileClient(
            _settings(), transport=transport_two, limiter=limiter, sleep=advance
        ) as second:
            for index in range(50):
                await (first if index % 2 else second).search_boards()
            await second.search_boards()
        self.assertEqual(delays, [60.0])


if __name__ == "__main__":
    unittest.main()
