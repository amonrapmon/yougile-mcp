"""Fake-transport contract tests for the shared YouGile API core."""

from __future__ import annotations

import asyncio
import json
import unittest
from itertools import count
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx

from yougile_mcp.api import (
    AuthenticationError,
    InvalidInputError,
    MissingCompanyIdError,
    MissingCredentialsError,
    NotFoundError,
    PaginationError,
    PaginationLimitError,
    PermissionDeniedError,
    RateLimitError,
    RequestTimeoutError,
    UncertainWriteError,
    UnsupportedOperationError,
    UpstreamError,
    VendorValidationError,
    YouGileClient,
)
from yougile_mcp.api.client import _decode_response
from yougile_mcp.api.spec import Operation, load_compatible_spec, load_spec, operations
from yougile_mcp.config import Settings


ROOT = Path(__file__).resolve().parents[1]
SECRET = "test-secret-do-not-log"
_TEST_COMPANIES = count()


def _settings(
    api_key: str | None = SECRET, *, company_id: str | None = None
) -> Settings:
    values = {} if api_key is None else {"YOUGILE_API_KEY": api_key}
    values["YOUGILE_COMPANY_ID"] = company_id or f"test-company-{next(_TEST_COMPANIES)}"
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


OPERATION_CASES = {
    "AuthKeyController_search": {
        "method": "POST",
        "path_template": "/api-v2/auth/keys/get",
        "expected_path": "/api-v2/auth/keys/get",
        "path": {},
        "query": {},
        "body": {"login": "user@example.test", "password": "test-password", "companyId": "company-1"},
        "authenticated": False,
        "invalid": {"body": None},
    },
    "ChatMessageController_get": {
        "method": "GET",
        "path_template": "/api-v2/chats/{chatId}/messages/{id}",
        "expected_path": "/api-v2/chats/chat%2F9/messages/42",
        "path": {"chatId": "chat/9", "id": 42},
        "query": {},
        "authenticated": True,
        "invalid": {"path": {"chatId": "chat/9"}},
    },
    "ChatMessageController_search": {
        "method": "GET",
        "path_template": "/api-v2/chats/{chatId}/messages",
        "expected_path": "/api-v2/chats/chat%2F9/messages",
        "path": {"chatId": "chat/9"},
        "query": {
            "includeDeleted": True,
            "limit": 10,
            "offset": 2,
            "fromUserId": "user-1",
            "text": "hello & hi",
            "label": "comment",
            "since": 1700000000000,
            "includeSystem": False,
        },
        "authenticated": True,
        "invalid": {"path": {}},
    },
    "CrmExternalIdController_findContactByExternalId": {
        "method": "GET",
        "path_template": "/api-v2/crm/contacts/by-external-id",
        "expected_path": "/api-v2/crm/contacts/by-external-id",
        "path": {},
        "query": {"provider": "telegram", "chatId": "external-user-1"},
        "authenticated": True,
        "invalid": {"query": {"chatId": "external-user-1"}},
    },
    "DepartmentController_get": {
        "method": "GET",
        "path_template": "/api-v2/departments/{id}",
        "expected_path": "/api-v2/departments/department%205",
        "path": {"id": "department 5"},
        "query": {},
        "authenticated": True,
        "invalid": {"path": {}},
    },
    "DepartmentController_search": {
        "method": "GET",
        "path_template": "/api-v2/departments",
        "expected_path": "/api-v2/departments",
        "path": {},
        "query": {
            "includeDeleted": False,
            "limit": 10,
            "offset": 2,
            "title": "Engineering",
            "parentId": "root/1",
        },
        "authenticated": True,
        "invalid": {"query": {"unknown": "value"}},
    },
    "ColumnController_get": {
        "method": "GET",
        "path_template": "/api-v2/columns/{id}",
        "expected_path": "/api-v2/columns/column%205",
        "path": {"id": "column 5"},
        "query": {},
        "authenticated": True,
        "invalid": {"path": {}},
    },
    "GroupChatController_get": {
        "method": "GET",
        "path_template": "/api-v2/group-chats/{id}",
        "expected_path": "/api-v2/group-chats/chat%201",
        "path": {"id": "chat 1"},
        "query": {},
        "authenticated": True,
        "invalid": {"path": {}},
    },
    "GroupChatController_search": {
        "method": "GET",
        "path_template": "/api-v2/group-chats",
        "expected_path": "/api-v2/group-chats",
        "path": {},
        "query": {
            "includeDeleted": True,
            "limit": 10,
            "offset": 2,
            "title": "Announcements",
        },
        "authenticated": True,
        "invalid": {"query": {"unknown": "value"}},
    },
    "ProjectController_get": {
        "method": "GET",
        "path_template": "/api-v2/projects/{id}",
        "expected_path": "/api-v2/projects/project%207",
        "path": {"id": "project 7"},
        "query": {},
        "authenticated": True,
        "invalid": {"path": {}},
    },
    "ProjectController_search": {
        "method": "GET",
        "path_template": "/api-v2/projects",
        "expected_path": "/api-v2/projects",
        "path": {},
        "query": {
            "includeDeleted": True,
            "limit": 10,
            "offset": 2,
            "title": "Research & Dev",
        },
        "authenticated": True,
        "invalid": {"query": {"unknown": "value"}},
    },
    "ProjectRolesController_get": {
        "method": "GET",
        "path_template": "/api-v2/projects/{projectId}/roles/{id}",
        "expected_path": "/api-v2/projects/project%2F7/roles/role%203",
        "path": {"projectId": "project/7", "id": "role 3"},
        "query": {},
        "authenticated": True,
        "invalid": {"path": {"projectId": "project/7"}},
    },
    "ProjectRolesController_search": {
        "method": "GET",
        "path_template": "/api-v2/projects/{projectId}/roles",
        "expected_path": "/api-v2/projects/project%2F7/roles",
        "path": {"projectId": "project/7"},
        "query": {"limit": 10, "offset": 2, "name": "Reviewer"},
        "authenticated": True,
        "invalid": {"path": {}},
    },
    "SprintStickerController_getSticker": {
        "method": "GET",
        "path_template": "/api-v2/sprint-stickers/{id}",
        "expected_path": "/api-v2/sprint-stickers/sprint%201",
        "path": {"id": "sprint 1"},
        "query": {},
        "authenticated": True,
        "invalid": {"path": {}},
    },
    "SprintStickerController_search": {
        "method": "GET",
        "path_template": "/api-v2/sprint-stickers",
        "expected_path": "/api-v2/sprint-stickers",
        "path": {},
        "query": {
            "includeDeleted": False,
            "limit": 10,
            "offset": 2,
            "name": "Sprint",
            "boardId": "board/1",
        },
        "authenticated": True,
        "invalid": {"query": {"unknown": "value"}},
    },
    "SprintStickerStateController_get": {
        "method": "GET",
        "path_template": "/api-v2/sprint-stickers/{stickerId}/states/{stickerStateId}",
        "expected_path": "/api-v2/sprint-stickers/sprint%202/states/state%203",
        "path": {"stickerId": "sprint 2", "stickerStateId": "state 3"},
        "query": {"includeDeleted": False},
        "authenticated": True,
        "invalid": {"path": {"stickerId": "sprint 2"}},
    },
    "StringStickerController_get": {
        "method": "GET",
        "path_template": "/api-v2/string-stickers/{id}",
        "expected_path": "/api-v2/string-stickers/sticker%201",
        "path": {"id": "sticker 1"},
        "query": {},
        "authenticated": True,
        "invalid": {"path": {}},
    },
    "StringStickerController_search": {
        "method": "GET",
        "path_template": "/api-v2/string-stickers",
        "expected_path": "/api-v2/string-stickers",
        "path": {},
        "query": {
            "includeDeleted": True,
            "limit": 10,
            "offset": 2,
            "name": "Priority",
            "boardId": "board/1",
        },
        "authenticated": True,
        "invalid": {"query": {"unknown": "value"}},
    },
    "StringStickerStateController_get": {
        "method": "GET",
        "path_template": "/api-v2/string-stickers/{stickerId}/states/{stickerStateId}",
        "expected_path": "/api-v2/string-stickers/sticker%202/states/state%201",
        "path": {"stickerId": "sticker 2", "stickerStateId": "state 1"},
        "query": {"includeDeleted": True},
        "authenticated": True,
        "invalid": {"path": {"stickerId": "sticker 2"}},
    },
    "TaskController_getChatSubscribers": {
        "method": "GET",
        "path_template": "/api-v2/tasks/{id}/chat-subscribers",
        "expected_path": "/api-v2/tasks/task%206/chat-subscribers",
        "path": {"id": "task 6"},
        "query": {},
        "authenticated": True,
        "invalid": {"path": {}},
    },
    "TaskController_getLog": {
        "method": "GET",
        "path_template": "/api-v2/tasks/{id}/log",
        "expected_path": "/api-v2/tasks/task%2F5/log",
        "path": {"id": "task/5"},
        "query": {"limit": 10, "before": 1700000000000},
        "authenticated": True,
        "invalid": {"path": {}},
    },
    "UserController_get": {
        "method": "GET",
        "path_template": "/api-v2/users/{id}",
        "expected_path": "/api-v2/users/user%2F42",
        "path": {"id": "user/42"},
        "query": {},
        "authenticated": True,
        "invalid": {"path": {}},
    },
    "UserController_getMe": {
        "method": "GET",
        "path_template": "/api-v2/users/me",
        "expected_path": "/api-v2/users/me",
        "path": {},
        "query": {},
        "authenticated": True,
        "invalid": {"query": {"unknown": "value"}},
    },
    "UserController_search": {
        "method": "GET",
        "path_template": "/api-v2/users",
        "expected_path": "/api-v2/users",
        "path": {},
        "query": {
            "limit": 10,
            "offset": 2,
            "email": "person@example.test",
            "projectId": "project / 1",
        },
        "authenticated": True,
        "invalid": {"query": {"unknown": "value"}},
    },
    "AuthKeyController_create": {
        "method": "POST",
        "path_template": "/api-v2/auth/keys",
        "expected_path": "/api-v2/auth/keys",
        "path": {},
        "query": {},
        "body": {"login": "user@example.test", "password": "test-password", "companyId": "company-1"},
        "status_code": 201,
        "authenticated": False,
        "invalid": {"body": {}},
    },
    "UserController_create": {
        "method": "POST",
        "path_template": "/api-v2/users",
        "expected_path": "/api-v2/users",
        "path": {},
        "query": {},
        "body": {"email": "new-user@example.test"},
        "status_code": 201,
        "authenticated": True,
        "invalid": {"body": {}},
    },
    "ProjectController_create": {
        "method": "POST",
        "path_template": "/api-v2/projects",
        "expected_path": "/api-v2/projects",
        "path": {},
        "query": {},
        "body": {"title": "Research"},
        "status_code": 201,
        "authenticated": True,
        "invalid": {"body": {}},
    },
    "ProjectRolesController_create": {
        "method": "POST",
        "path_template": "/api-v2/projects/{projectId}/roles",
        "expected_path": "/api-v2/projects/project%2F7/roles",
        "path": {"projectId": "project/7"},
        "query": {},
        "body": {
            "name": "Reviewer",
            "permissions": {
                "editTitle": False,
                "delete": False,
                "addBoard": False,
                "boards": {
                    "editTitle": False,
                    "delete": False,
                    "move": False,
                    "showStickers": False,
                    "editStickers": False,
                    "addColumn": False,
                    "columns": {
                        "editTitle": False,
                        "delete": False,
                        "move": "no",
                        "addTask": False,
                        "allTasks": {
                            "show": False,
                            "delete": False,
                            "editTitle": False,
                            "editDescription": False,
                            "complete": False,
                            "close": False,
                            "assignUsers": "no",
                            "connect": False,
                            "editSubtasks": "no",
                            "editStickers": False,
                            "editPins": False,
                            "move": "no",
                            "sendMessages": False,
                            "sendFiles": False,
                            "editWhoToNotify": "no",
                        },
                        "withMeTasks": {
                            "show": False,
                            "delete": False,
                            "editTitle": False,
                            "editDescription": False,
                            "complete": False,
                            "close": False,
                            "assignUsers": "no",
                            "connect": False,
                            "editSubtasks": "no",
                            "editStickers": False,
                            "editPins": False,
                            "move": "no",
                            "sendMessages": False,
                            "sendFiles": False,
                            "editWhoToNotify": "no",
                        },
                        "myTasks": {
                            "show": False,
                            "delete": False,
                            "editTitle": False,
                            "editDescription": False,
                            "complete": False,
                            "close": False,
                            "assignUsers": "no",
                            "connect": False,
                            "editSubtasks": "no",
                            "editStickers": False,
                            "editPins": False,
                            "move": "no",
                            "sendMessages": False,
                            "sendFiles": False,
                            "editWhoToNotify": "no",
                        },
                        "createdByMeTasks": {
                            "show": False,
                            "delete": False,
                            "editTitle": False,
                            "editDescription": False,
                            "complete": False,
                            "close": False,
                            "assignUsers": "no",
                            "connect": False,
                            "editSubtasks": "no",
                            "editStickers": False,
                            "editPins": False,
                            "move": "no",
                            "sendMessages": False,
                            "sendFiles": False,
                            "editWhoToNotify": "no",
                        },
                    },
                    "settings": False,
                },
            },
        },
        "status_code": 201,
        "authenticated": True,
        "invalid": {"path": {"projectId": "project/7"}, "body": {}},
    },
    "DepartmentController_create": {
        "method": "POST",
        "path_template": "/api-v2/departments",
        "expected_path": "/api-v2/departments",
        "path": {},
        "query": {},
        "body": {"title": "Engineering"},
        "status_code": 201,
        "authenticated": True,
        "invalid": {"body": {}},
    },
    "BoardController_create": {
        "method": "POST",
        "path_template": "/api-v2/boards",
        "expected_path": "/api-v2/boards",
        "path": {},
        "query": {},
        "body": {"title": "Sprint board", "projectId": "project-1"},
        "status_code": 201,
        "authenticated": True,
        "invalid": {"body": {}},
    },
    "TaskController_create": {
        "method": "POST",
        "path_template": "/api-v2/tasks",
        "expected_path": "/api-v2/tasks",
        "path": {},
        "query": {},
        "body": {"title": "Review API"},
        "status_code": 201,
        "authenticated": True,
        "invalid": {"body": {}},
    },
    "StringStickerController_create": {
        "method": "POST",
        "path_template": "/api-v2/string-stickers",
        "expected_path": "/api-v2/string-stickers",
        "path": {},
        "query": {},
        "body": {"name": "Priority"},
        "status_code": 201,
        "authenticated": True,
        "invalid": {"body": {}},
    },
    "StringStickerStateController_create": {
        "method": "POST",
        "path_template": "/api-v2/string-stickers/{stickerId}/states",
        "expected_path": "/api-v2/string-stickers/sticker%2F2/states",
        "path": {"stickerId": "sticker/2"},
        "query": {},
        "body": {"name": "Ready", "color": "green"},
        "status_code": 201,
        "authenticated": True,
        "invalid": {"path": {"stickerId": "sticker/2"}, "body": {}},
    },
    "SprintStickerController_create": {
        "method": "POST",
        "path_template": "/api-v2/sprint-stickers",
        "expected_path": "/api-v2/sprint-stickers",
        "path": {},
        "query": {},
        "body": {"name": "Iteration"},
        "status_code": 201,
        "authenticated": True,
        "invalid": {"body": {}},
    },
    "SprintStickerStateController_create": {
        "method": "POST",
        "path_template": "/api-v2/sprint-stickers/{stickerId}/states",
        "expected_path": "/api-v2/sprint-stickers/sprint%2F2/states",
        "path": {"stickerId": "sprint/2"},
        "query": {},
        "body": {"name": "Active", "begin": 1700000000000, "end": 1700003600000},
        "status_code": 201,
        "authenticated": True,
        "invalid": {"path": {"stickerId": "sprint/2"}, "body": {}},
    },
    "GroupChatController_create": {
        "method": "POST",
        "path_template": "/api-v2/group-chats",
        "expected_path": "/api-v2/group-chats",
        "path": {},
        "query": {},
        "body": {"title": "Team updates", "users": {}, "userRoleMap": {}, "roleConfigMap": {}},
        "status_code": 201,
        "authenticated": True,
        "invalid": {"body": {}},
    },
    "ChatMessageController_sendMessage": {
        "method": "POST",
        "path_template": "/api-v2/chats/{chatId}/messages",
        "expected_path": "/api-v2/chats/chat%2F2/messages",
        "path": {"chatId": "chat/2"},
        "query": {},
        "body": {"text": "Review", "textHtml": "<p>Review</p>", "label": "comment"},
        "status_code": 201,
        "authenticated": True,
        "invalid": {"path": {"chatId": "chat/2"}, "body": {}},
    },
    "CrmContactPersonsController_create": {
        "method": "POST",
        "path_template": "/api-v2/crm/contact-persons",
        "expected_path": "/api-v2/crm/contact-persons",
        "path": {},
        "query": {},
        "body": {"projectId": "project-1", "title": "Alex Example"},
        "status_code": 201,
        "authenticated": True,
        "invalid": {"body": {}},
    },
    "BoardController_update": {
        "method": "PUT",
        "path_template": "/api-v2/boards/{id}",
        "expected_path": "/api-v2/boards/board%2F7",
        "path": {"id": "board/7"},
        "query": {},
        "body": {"title": "Sprint planning", "deleted": False},
        "authenticated": True,
        "invalid": {"path": {"id": "board/7"}, "body": {"title": None}},
    },
    "ChatMessageController_typing": {
        "method": "POST",
        "path_template": "/api-v2/chats/{chatId}/typing",
        "expected_path": "/api-v2/chats/chat%2F3/typing",
        "path": {"chatId": "chat/3"},
        "query": {},
        "authenticated": True,
        "invalid": {"path": {}},
    },
    "ChatMessageController_update": {
        "method": "PUT",
        "path_template": "/api-v2/chats/{chatId}/messages/{id}",
        "expected_path": "/api-v2/chats/chat%2F3/messages/18",
        "path": {"chatId": "chat/3", "id": 18},
        "query": {},
        "body": {"label": "comment", "react": "👍"},
        "authenticated": True,
        "invalid": {"path": {"chatId": "chat/3", "id": 18}, "body": {"label": 1}},
    },
    "ColumnController_update": {
        "method": "PUT",
        "path_template": "/api-v2/columns/{id}",
        "expected_path": "/api-v2/columns/column%208",
        "path": {"id": "column 8"},
        "query": {},
        "body": {"title": "Ready", "color": 2, "boardId": "board-1"},
        "authenticated": True,
        "invalid": {"path": {"id": "column 8"}, "body": {"color": "blue"}},
    },
    "DepartmentController_update": {
        "method": "PUT",
        "path_template": "/api-v2/departments/{id}",
        "expected_path": "/api-v2/departments/department%2F1",
        "path": {"id": "department/1"},
        "query": {},
        "body": {"title": "Operations", "parentId": "parent-1"},
        "authenticated": True,
        "invalid": {"path": {"id": "department/1"}, "body": {"title": None}},
    },
    "GroupChatController_update": {
        "method": "PUT",
        "path_template": "/api-v2/group-chats/{id}",
        "expected_path": "/api-v2/group-chats/chat%205",
        "path": {"id": "chat 5"},
        "query": {},
        "body": {"title": "Team updates", "users": {}, "userRoleMap": {}, "roleConfigMap": {}},
        "authenticated": True,
        "invalid": {"path": {"id": "chat 5"}, "body": {"title": 7}},
    },
    "ProjectController_update": {
        "method": "PUT",
        "path_template": "/api-v2/projects/{id}",
        "expected_path": "/api-v2/projects/project%2F2",
        "path": {"id": "project/2"},
        "query": {},
        "body": {"title": "Updated project", "deleted": False},
        "authenticated": True,
        "invalid": {"path": {"id": "project/2"}, "body": {"title": None}},
    },
    "ProjectRolesController_update": {
        "method": "PUT",
        "path_template": "/api-v2/projects/{projectId}/roles/{id}",
        "expected_path": "/api-v2/projects/project%2F9/roles/role%202",
        "path": {"projectId": "project/9", "id": "role 2"},
        "query": {},
        "body": {"name": "Manager"},
        "authenticated": True,
        "invalid": {"path": {"projectId": "project/9", "id": "role 2"}, "body": {"name": 1}},
    },
    "SprintStickerController_update": {
        "method": "PUT",
        "path_template": "/api-v2/sprint-stickers/{id}",
        "expected_path": "/api-v2/sprint-stickers/sprint-2",
        "path": {"id": "sprint-2"},
        "query": {},
        "body": {"name": "Iteration 2"},
        "authenticated": True,
        "invalid": {"path": {"id": "sprint-2"}, "body": {"name": None}},
    },
    "SprintStickerStateController_update": {
        "method": "PUT",
        "path_template": "/api-v2/sprint-stickers/{stickerId}/states/{stickerStateId}",
        "expected_path": "/api-v2/sprint-stickers/sprint%2F2/states/state%203",
        "path": {"stickerId": "sprint/2", "stickerStateId": "state 3"},
        "query": {},
        "body": {"name": "Active", "begin": 1700000000000, "end": 1700003600000},
        "authenticated": True,
        "invalid": {"path": {"stickerId": "sprint/2", "stickerStateId": "state 3"}, "body": {"begin": "now"}},
    },
    "StringStickerController_update": {
        "method": "PUT",
        "path_template": "/api-v2/string-stickers/{id}",
        "expected_path": "/api-v2/string-stickers/sticker-1",
        "path": {"id": "sticker-1"},
        "query": {},
        "body": {"name": "Priority", "icon": "star"},
        "authenticated": True,
        "invalid": {"path": {"id": "sticker-1"}, "body": {"icon": "unsupported"}},
    },
    "StringStickerStateController_update": {
        "method": "PUT",
        "path_template": "/api-v2/string-stickers/{stickerId}/states/{stickerStateId}",
        "expected_path": "/api-v2/string-stickers/sticker%2F3/states/state%2F2",
        "path": {"stickerId": "sticker/3", "stickerStateId": "state/2"},
        "query": {},
        "body": {"name": "Ready", "color": "green"},
        "authenticated": True,
        "invalid": {"path": {"stickerId": "sticker/3", "stickerStateId": "state/2"}, "body": {"color": False}},
    },
    "TaskController_update": {
        "method": "PUT",
        "path_template": "/api-v2/tasks/{id}",
        "expected_path": "/api-v2/tasks/task%2F9",
        "path": {"id": "task/9"},
        "query": {},
        "body": {"title": "Review API", "color": "task-primary"},
        "authenticated": True,
        "invalid": {"path": {"id": "task/9"}, "body": {"title": None}},
    },
    "TaskController_updateChatSubscribers": {
        "method": "PUT",
        "path_template": "/api-v2/tasks/{id}/chat-subscribers",
        "expected_path": "/api-v2/tasks/task%207/chat-subscribers",
        "path": {"id": "task 7"},
        "query": {},
        "body": {"content": ["user-1", "user-2"]},
        "authenticated": True,
        "invalid": {"path": {"id": "task 7"}, "body": {"content": "user-1"}},
    },
    "UserController_setCustomStatus": {
        "method": "PUT",
        "path_template": "/api-v2/users/me/custom-status",
        "expected_path": "/api-v2/users/me/custom-status",
        "path": {},
        "query": {},
        "body": {"emoji": "wave", "text": "Reviewing API"},
        "authenticated": True,
        "invalid": {"body": {}},
    },
    "UserController_update": {
        "method": "PUT",
        "path_template": "/api-v2/users/{id}",
        "expected_path": "/api-v2/users/user%2F8",
        "path": {"id": "user/8"},
        "query": {},
        "body": {"isAdmin": False},
        "authenticated": True,
        "invalid": {"path": {"id": "user/8"}, "body": {"isAdmin": "no"}},
    },
    "AuthKeyController_delete": {
        "method": "DELETE",
        "path_template": "/api-v2/auth/keys/{key}",
        "expected_path": "/api-v2/auth/keys/key%2F1",
        "path": {"key": "key/1"},
        "query": {},
        "status_code": 200,
        "empty_response": True,
        "authenticated": False,
        "invalid": {"path": {}},
    },
    "ProjectRolesController_delete": {
        "method": "DELETE",
        "path_template": "/api-v2/projects/{projectId}/roles/{id}",
        "expected_path": "/api-v2/projects/project%2F9/roles/role%202",
        "path": {"projectId": "project/9", "id": "role 2"},
        "query": {},
        "authenticated": True,
        "invalid": {"path": {"projectId": "project/9"}},
    },
    "UserController_clearCustomStatus": {
        "method": "DELETE",
        "path_template": "/api-v2/users/me/custom-status",
        "expected_path": "/api-v2/users/me/custom-status",
        "path": {},
        "query": {},
        "authenticated": True,
        "invalid": {"query": {"unknown": "value"}},
    },
    "UserController_delete": {
        "method": "DELETE",
        "path_template": "/api-v2/users/{id}",
        "expected_path": "/api-v2/users/user%2F8",
        "path": {"id": "user/8"},
        "query": {},
        "authenticated": True,
        "invalid": {"path": {}},
    },
    "CompanyController_get": {
        "method": "GET",
        "path_template": "/api-v2/companies{*companyId}",
        "expected_path": "/api-v2/companies",
        "path": {},
        "query": {},
        "response_body": {
            "title": "Example company",
            "timestamp": 1700000000000,
            "id": "company-1",
            "deleted": None,
        },
        "authenticated": True,
        "invalid": {"path": {"companyId": "company-1"}},
    },
    "CompanyController_update": {
        "method": "PUT",
        "path_template": "/api-v2/companies{*companyId}",
        "expected_path": "/api-v2/companies",
        "path": {},
        "query": {},
        "body": {"title": "Mock-only company title"},
        "authenticated": True,
        "invalid": {"body": {"title": False}},
    },
    "WebhookController_create": {
        "method": "POST",
        "path_template": "/api-v2/webhooks",
        "expected_path": "/api-v2/webhooks",
        "path": {},
        "query": {},
        "body": {
            "url": "https://receiver.example.test",
            "event": "task-created",
            "filters": [{"name": "title", "value": "^GEN214_TEST_ONLY$"}],
        },
        "status_code": 201,
        "authenticated": True,
        "invalid": {
            "body": {
                "url": "https://receiver.example.test",
                "event": "task-created",
                "filters": [{"name": "title", "value": 42}],
            }
        },
    },
    "WebhookController_put": {
        "method": "PUT",
        "path_template": "/api-v2/webhooks/{id}",
        "expected_path": "/api-v2/webhooks/webhook%2Ftest",
        "path": {"id": "webhook/test"},
        "query": {},
        "body": {"disabled": True},
        "authenticated": True,
        "invalid": {"body": {"disabled": "true"}},
    },
    "WebhookController_search": {
        "method": "GET",
        "path_template": "/api-v2/webhooks",
        "expected_path": "/api-v2/webhooks",
        "path": {},
        "query": {"includeDeleted": True},
        "response_body": [
            {
                "id": "webhook-test",
                "event": "task-created",
                "url": "https://receiver.example.test",
                "filters": [{"name": "title", "value": "^GEN214_TEST_ONLY$"}],
                "failuresSinceLastSuccess": 0,
                "disabled": True,
            }
        ],
        "authenticated": True,
        "invalid": {"query": {"includeDeleted": "true"}},
    },
    "FileController_uploadFile": {
        "method": "POST",
        "path_template": "/api-v2/upload-file",
        "expected_path": "/api-v2/upload-file",
        "path": {},
        "query": {},
        "multipart_file": ("contract.txt", b"mock upload", "text/plain"),
        "status_code": 201,
        "response_body": {
            "result": "ok",
            "url": "/uploads/mock.txt",
            "fullUrl": "https://ru.yougile.com/uploads/mock.txt",
        },
        "authenticated": True,
        "invalid": {
            "multipart_file": ("../contract.txt", b"mock upload", "text/plain")
        },
    },
}


def _sample_schema(schema: dict[str, Any], spec: dict[str, Any] | None = None) -> Any:
    spec = spec or load_spec()
    if "$ref" in schema:
        target: Any = spec
        for part in schema["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        return _sample_schema(target, spec)
    if "enum" in schema:
        return schema["enum"][0]
    for union in ("oneOf", "anyOf"):
        if union in schema:
            return _sample_schema(schema[union][0], spec)
    result: dict[str, Any] = {}
    for part in schema.get("allOf", []):
        example = _sample_schema(part, spec)
        if isinstance(example, dict):
            result.update(example)
        elif not result:
            return example
    schema_type = schema.get("type")
    if schema_type == "array":
        if schema.get("maxItems") == 0:
            return []
        return [_sample_schema(schema.get("items", {}), spec)]
    if schema_type == "object" or "properties" in schema:
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            result[name] = _sample_schema(properties[name], spec)
        return result
    if schema_type == "string":
        return "sample"
    if schema_type in {"number", "integer"}:
        return schema.get("minimum", 1)
    if schema_type == "boolean":
        return False
    if schema_type == "null":
        return None
    return result


def _sample_operation_response(operation_id: str, status_code: int = 200) -> Any:
    operation = load_spec()["paths"]
    raw_operation = next(
        raw
        for path_item in operation.values()
        for method, raw in path_item.items()
        if method in {"get", "post", "put", "patch", "delete"}
        and raw.get("operationId") == operation_id
    )
    schema = raw_operation["responses"][str(status_code)]["content"]["application/json"]["schema"]
    return _sample_schema(schema)


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

    async def test_read_only_post_timeout_and_rate_limit_use_read_semantics(self):
        calls = 0

        def timeout_handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            raise httpx.ReadTimeout("timeout", request=request)

        async with YouGileClient(
            _settings(None), transport=httpx.MockTransport(timeout_handler), sleep=_no_sleep
        ) as client:
            with self.assertRaises(RequestTimeoutError):
                await client.get_companies({"login": "user@example.test", "password": SECRET})
        self.assertEqual(calls, 1)

        calls = 0

        def rate_limit_handler(_: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls == 1:
                return httpx.Response(429, headers={"Retry-After": "0"})
            return httpx.Response(200, json=_page(0, [], next_page=False))

        async with YouGileClient(
            _settings(None), transport=httpx.MockTransport(rate_limit_handler), sleep=_no_sleep
        ) as client:
            result = await client.get_companies(
                {"login": "user@example.test", "password": SECRET}
            )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(calls, 2)

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
            await client.search_tasks({"columnId": "column-1"}, reversed_order=False)
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

    async def test_missing_company_id_fails_before_protected_http_call(self):
        calls = 0

        def handler(_: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(200, json=_page(0, [], next_page=False))

        settings = Settings.from_env({"YOUGILE_API_KEY": SECRET})
        async with YouGileClient(
            settings, transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            with self.assertRaises(MissingCompanyIdError):
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

    async def test_destructive_timeout_is_uncertain_and_never_retried(self):
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            raise httpx.ReadTimeout("timeout", request=request)

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            with self.assertRaises(UncertainWriteError):
                await client.request("UserController_delete", path={"id": "user/8"})
        self.assertEqual(calls, 1)

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
            effect="read",
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

    async def test_response_schema_matches_actual_content_type(self):
        operation = Operation(
            operation_id="multi-media",
            method="GET",
            path="/multi-media",
            effect="read",
            parameters=(),
            request_body=None,
            responses={
                "200": {
                    "content": {
                        "application/json": {"schema": {"type": "object"}},
                        "text/plain": {"schema": {"type": "string"}},
                    }
                }
            },
            security=(),
        )
        result = _decode_response(
            operation,
            httpx.Response(
                200,
                headers={"Content-Type": "text/plain; charset=utf-8"},
                content=b"plain response",
            ),
        )
        self.assertEqual(result.data, "plain response")

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

    async def test_list_all_supports_other_offset_paged_operations(self):
        page = _sample_operation_response("ProjectRolesController_search")
        page["paging"].update({"count": 1, "limit": 1, "offset": 0, "next": False})
        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json=page)

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            roles = await client.list_all(
                "ProjectRolesController_search",
                path={"projectId": "project/7"},
                query={"limit": 1},
            )
            with self.assertRaises(UnsupportedOperationError):
                await client.list_all("UserController_getMe")

        self.assertEqual(roles, page["content"])
        self.assertEqual(len(seen), 1)
        self.assertEqual(
            seen[0].url.raw_path.split(b"?", 1)[0],
            b"/api-v2/projects/project%2F7/roles",
        )
        self.assertEqual(dict(seen[0].url.params), {"limit": "1", "offset": "0"})

    async def test_task_log_cursor_pagination_uses_last_event_timestamp(self):
        pages = [
            {
                "paging": {"count": 2, "limit": 2, "next": True},
                "content": [
                    {"timestamp": 30, "type": "add"},
                    {"timestamp": 20, "type": "rename"},
                ],
            },
            {
                "paging": {"count": 1, "limit": 2, "next": False},
                "content": [{"timestamp": 10, "type": "move"}],
            },
        ]
        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json=pages.pop(0))

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            entries = await client.list_all(
                "TaskController_getLog",
                path={"id": "task/5"},
                query={"limit": 2},
            )

        self.assertEqual([entry["timestamp"] for entry in entries], [30, 20, 10])
        self.assertEqual(
            [request.url.raw_path.split(b"?", 1)[0] for request in seen],
            [b"/api-v2/tasks/task%2F5/log"] * 2,
        )
        self.assertEqual(dict(seen[0].url.params), {"limit": "2"})
        self.assertEqual(dict(seen[1].url.params), {"limit": "2", "before": "20"})

    async def test_task_log_cursor_rejects_stalls_and_page_budget_overflow(self):
        calls = 0

        def stalled_handler(_: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(
                200,
                json={
                    "paging": {"count": 1, "limit": 1, "next": True},
                    "content": [{"timestamp": 20, "type": "add"}],
                },
            )

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(stalled_handler), sleep=_no_sleep
        ) as client:
            with self.assertRaises(PaginationError):
                await client.list_all(
                    "TaskController_getLog", path={"id": "task-1"}, query={"limit": 1}
                )
        self.assertEqual(calls, 2)

        def more_pages(_: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "paging": {"count": 1, "limit": 1, "next": True},
                    "content": [{"timestamp": 20, "type": "add"}],
                },
            )

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(more_pages), sleep=_no_sleep
        ) as client:
            with self.assertRaises(PaginationLimitError):
                await client.list_all(
                    "TaskController_getLog",
                    path={"id": "task-1"},
                    query={"limit": 1},
                    max_pages=1,
                )

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

        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_page(0, [], next_page=False))

        with patch("yougile_mcp.api.client.time.monotonic", side_effect=lambda: now[0]):
            async with YouGileClient(
                _settings("first-key", company_id="shared-company"),
                transport=httpx.MockTransport(handler),
                sleep=advance,
            ) as first, YouGileClient(
                _settings("second-key", company_id="shared-company"),
                transport=httpx.MockTransport(handler),
                sleep=advance,
            ) as second:
                self.assertIs(first._limiter, second._limiter)
                for index in range(50):
                    await (first if index % 2 else second).search_boards()
                await second.search_boards()
        self.assertEqual(delays, [60.0])

    async def test_operation_contracts(self):
        for operation_id, case in OPERATION_CASES.items():
            with self.subTest(operation_id=operation_id):
                seen = []
                status_code = case.get("status_code", 200)
                empty_response = case.get("empty_response", False)
                response_body = case.get("response_body")
                if "response_body" not in case:
                    response_body = (
                        None
                        if empty_response
                        else _sample_operation_response(operation_id, status_code)
                    )
                expected_effect = (
                    "read"
                    if case["method"] == "GET" or operation_id == "AuthKeyController_search"
                    else "destructive"
                    if case["method"] == "DELETE"
                    else "write"
                )
                self.assertEqual(operations()[operation_id].effect, expected_effect)

                def handler(request: httpx.Request) -> httpx.Response:
                    seen.append(request)
                    return (
                        httpx.Response(status_code)
                        if empty_response
                        else httpx.Response(status_code, json=response_body)
                    )

                async with YouGileClient(
                    _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
                ) as client:
                    with self.assertRaises(InvalidInputError):
                        await client.request(operation_id=operation_id, **case["invalid"])
                    self.assertEqual(seen, [])

                    result = await client.request(
                        operation_id=operation_id,
                        path=case["path"],
                        query=case["query"],
                        body=case.get("body"),
                        multipart_file=case.get("multipart_file"),
                    )

                self.assertEqual(result.status_code, status_code)
                self.assertEqual(result.data, response_body)
                self.assertEqual(len(seen), 1)
                request = seen[0]
                self.assertEqual(request.method, case["method"])
                self.assertEqual(
                    request.url.raw_path.split(b"?", 1)[0].decode("ascii"),
                    case["expected_path"],
                )
                self.assertEqual(
                    dict(request.url.params),
                    {
                        key: str(value).lower() if isinstance(value, bool) else str(value)
                        for key, value in case["query"].items()
                    },
                )
                if case["authenticated"]:
                    self.assertEqual(request.headers["Authorization"], f"Bearer {SECRET}")
                else:
                    self.assertNotIn("Authorization", request.headers)
                if case.get("multipart_file") is not None:
                    filename, content, part_content_type = case["multipart_file"]
                    self.assertTrue(request.headers["Content-Type"].startswith("multipart/form-data; boundary="))
                    self.assertIn(f'filename="{filename}"'.encode(), request.content)
                    self.assertIn(content, request.content)
                    self.assertIn(f"Content-Type: {part_content_type}".encode(), request.content)
                elif case.get("body") is not None:
                    self.assertEqual(request.headers["Content-Type"], "application/json")
                    self.assertEqual(json.loads(request.content), case["body"])
                else:
                    self.assertEqual(request.content, b"")
                print(f"MockTransport contract passed: {operation_id}")

    async def test_compatibility_overlay_uses_canonical_routes_without_mutating_vendor_spec(self):
        spec = load_spec()
        compatible = load_compatible_spec()
        raw_company_path = "/api-v2/companies{*companyId}"
        self.assertIn(raw_company_path, spec["paths"])
        self.assertEqual(
            spec["components"]["schemas"]["WebhookFilters"]["properties"]["name"]["items"]["type"],
            "location",
        )
        self.assertEqual(
            spec["paths"]["/api-v2/upload-file"]["post"]["requestBody"]["content"]["multipart/form-data"]["schema"]["$ref"],
            "#/components/schemas/",
        )
        self.assertTrue(
            compatible["components"]["schemas"]["CompanyDto"]["properties"]["deleted"]["nullable"]
        )
        self.assertEqual(
            compatible["components"]["schemas"]["WebhookFilters"]["properties"],
            {"name": {"type": "string"}, "value": {"type": "string"}},
        )
        upload_schema = compatible["paths"]["/api-v2/upload-file"]["post"]["requestBody"]["content"]["multipart/form-data"]["schema"]
        self.assertNotIn("$ref", upload_schema)
        self.assertEqual(upload_schema["properties"]["file"], {"type": "string", "format": "binary"})
        self.assertEqual(operations()["CompanyController_get"].path, "/api-v2/companies")
        self.assertEqual(operations()["CompanyController_update"].path, "/api-v2/companies")
        self.assertEqual(operations()["WebhookController_search"].responses["200"]["content"]["application/json"]["schema"]["type"], "array")
        self.assertIn("201", operations()["FileController_uploadFile"].responses)
        self.assertEqual(spec["paths"][raw_company_path]["get"]["operationId"], "CompanyController_get")

    async def test_upload_policy_is_configurable_and_accepts_binary_multipart(self):
        seen = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(
                201,
                json={"result": "ok", "url": "/uploads/binary.bin", "fullUrl": "https://ru.yougile.com/uploads/binary.bin"},
            )

        async with YouGileClient(
            _settings(),
            transport=httpx.MockTransport(handler),
            sleep=_no_sleep,
            max_upload_bytes=4,
            allowed_upload_content_types={"application/octet-stream"},
        ) as client:
            result = await client.upload_file(
                filename="payload.bin",
                content=b"\x00\xffab",
                content_type="application/octet-stream",
            )

        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.data["result"], "ok")
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0].method, "POST")
        self.assertEqual(seen[0].url.path, "/api-v2/upload-file")
        self.assertEqual(seen[0].headers["Authorization"], f"Bearer {SECRET}")
        self.assertTrue(seen[0].headers["Content-Type"].startswith("multipart/form-data; boundary="))
        self.assertIn(b'name="file"; filename="payload.bin"', seen[0].content)
        self.assertIn(b"\x00\xffab", seen[0].content)

    async def test_upload_rejects_unsafe_filename_size_and_mime_before_http(self):
        calls = 0

        def handler(_: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(200, json={})

        async with YouGileClient(
            _settings(),
            transport=httpx.MockTransport(handler),
            sleep=_no_sleep,
            max_upload_bytes=10,
        ) as client:
            for filename, content, content_type in (
                ("../unsafe.txt", b"ok", "text/plain"),
                ("too-large.txt", b"12345678901", "text/plain"),
                ("wrong-type.bin", b"ok", "application/octet-stream"),
            ):
                with self.subTest(filename=filename):
                    with self.assertRaises(InvalidInputError):
                        await client.upload_file(
                            filename=filename, content=content, content_type=content_type
                        )
        self.assertEqual(calls, 0)

    async def test_upload_timeout_is_uncertain_and_not_retried(self):
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            raise httpx.ReadTimeout("timed out", request=request)

        async with YouGileClient(
            _settings(), transport=httpx.MockTransport(handler), sleep=_no_sleep
        ) as client:
            with self.assertRaises(UncertainWriteError):
                await client.upload_file(
                    filename="small.txt", content=b"safe", content_type="text/plain"
                )
        self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
