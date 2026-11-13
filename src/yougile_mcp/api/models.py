"""Typed request and response shapes for the currently tested API slice."""

# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, NotRequired, TypedDict, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class ApiResponse(Generic[T]):
    status_code: int
    data: T | None


class PagingMetadata(TypedDict):
    count: int | float
    limit: int | float
    offset: int | float
    next: bool


class Board(TypedDict):
    id: str
    title: str
    projectId: str


class BoardDto(Board, total=False):
    deleted: bool
    stickers: dict[str, Any]


class BoardListDto(TypedDict):
    paging: PagingMetadata
    content: list[Board]


class Company(TypedDict):
    id: str
    name: str
    isAdmin: bool


class CompanyListDto(TypedDict):
    paging: PagingMetadata
    content: list[Company]


class CompanyCredentials(TypedDict):
    login: str
    password: str
    name: NotRequired[str]


class CompanySearchQuery(TypedDict, total=False):
    limit: int
    offset: int


class Column(TypedDict):
    id: str
    title: str
    boardId: str


class ColumnListDto(TypedDict):
    paging: PagingMetadata
    content: list[Column]


class Task(TypedDict):
    id: str
    title: str
    timestamp: int | float


class TaskDto(Task, total=False):
    deleted: bool
    columnId: str
    description: str
    archived: bool
    archivedTimestamp: int | float
    completed: bool
    completedTimestamp: int | float
    subtasks: list[str]
    assigned: list[str]
    createdBy: str
    stickers: dict[str, Any]
    apiData: dict[str, Any]
    extensionData: dict[str, Any]
    properties: dict[str, Any]


class TaskListDto(TypedDict):
    paging: PagingMetadata
    content: list[Task]


class BoardSearchQuery(TypedDict, total=False):
    includeDeleted: bool
    limit: int
    offset: int
    title: str
    projectId: str


class ColumnSearchQuery(TypedDict, total=False):
    includeDeleted: bool
    limit: int
    offset: int
    title: str
    boardId: str


class TaskSearchQuery(TypedDict, total=False):
    includeDeleted: bool
    limit: int
    offset: int
    title: str
    columnId: str
    assignedTo: str
    stickerId: str
    stickerStateId: str


class CreateColumnDto(TypedDict):
    title: str
    boardId: str
    color: NotRequired[int | float]
    idempotencyKey: NotRequired[str]


class WithIdDto(TypedDict):
    id: str
