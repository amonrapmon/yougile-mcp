"""Indalo's server-rendered admin layout, adapted to the Full Access runtime.

Layout, responsive tables, staff screens, navigation and action forms are
adapted from indalo-tech/yougile-mcp-cloud/admin_pages.py at ea88a0d5,
Copyright (c) Indalo, AGPL-3.0-only. Uses Indalo's reused pages.py / CSS.

The upstream's roles/project allowlists/workflows are NOT represented as
fake controls: they depend on a different policy engine. This UI renders
the actual cloud-company status and member lifecycle supported by our DB.
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote

from .pages import e, page


@dataclass(frozen=True)
class Frame:
    company_id: str
    company_name: str
    enabled: bool
    admin_name: str
    csrf: str
    member_count: int = 0
    connected_count: int = 0
    blocked_count: int = 0


@dataclass(frozen=True)
class Person:
    id: str
    name: str
    email: str
    yougile_admin: bool
    in_yougile: bool
    connected: bool
    blocked: bool
    last_connected: datetime | None = None


_DONE = {
    "disconnect": "Сотрудник отключён от YouGile MCP. Он сможет войти снова.",
    "block": "Подключение сотрудника запрещено. Активные сеансы отключены.",
    "unblock": "Запрет снят. Сотрудник может подключиться снова.",
}


def _csrf(token: str) -> str:
    return f'<input type="hidden" name="csrf" value="{e(token)}">'


def _shell(
    frame: Frame, current: str, title: str, body: str, done: str | None = None,
) -> str:
    # Based on Indalo's original _shell; the shared CSS/HTML is unchanged.
    links = [("users", "/admin", "Сотрудники"), ("settings", "/admin/settings", "Настройки")]
    nav = "".join(
        f'<a href="{href}"{" aria-current=page" if key == current else ""}>{e(label)}</a>'
        for key, href, label in links
    )
    notice = (
        f'<div class="ok" role="status">{e(_DONE[done])}</div>'
        if done in _DONE else ""
    )
    status = "Работает" if frame.enabled else "Отключено владельцем сервера"
    return page(
        title,
        f'<div class="top"><div><h1>{e(frame.company_name)}</h1>'
        f'<p class="lead">YouGile MCP · {e(status)} · {e(frame.admin_name)}</p></div>'
        f'<form method="post" action="/admin/logout">{_csrf(frame.csrf)}'
        '<button class="inline secondary" type="submit">Выйти</button></form></div>'
        f"<nav>{nav}</nav>{notice}{body}",
        wide=True,
    )


def _href(person: Person) -> str:
    return e(f"/admin/users/{quote(person.id, safe='')}")


def _pills(person: Person) -> str:
    return (
        ('<span class="pill">админ YouGile</span>' if person.yougile_admin else "")
        + ("" if person.in_yougile else '<span class="pill">нет в YouGile</span>')
        + ('<span class="pill">подключение запрещено</span>' if person.blocked else "")
    )


def _mcp_cell(person: Person) -> str:
    if not person.connected:
        return '<span class="muted">нет подключения</span>'
    date = (
        person.last_connected.strftime("%d.%m.%Y %H:%M UTC")
        if person.last_connected is not None else ""
    )
    return "подключено" + (
        f'<div class="muted">обновлено {e(date)}</div>' if date else ""
    )


def users_page(frame: Frame, people: list[Person], done: str | None = None) -> str:
    # Ported from Indalo's users_page, with real connection states.
    rows = []
    for person in people:
        status = (
            "Запрещено" if person.blocked else
            "Подключён" if person.connected else "Не подключён"
        )
        link = _href(person)
        rows.append(
            f'<tr><td><a href="{link}"><b>{e(person.name)}</b></a>'
            f'<div class="muted">{e(person.email)}</div>{_pills(person)}</td>'
            f"<td>{_mcp_cell(person)}</td>"
            f'<td data-label="Статус">{e(status)}</td>'
            f'<td><a href="{link}">Настроить</a></td></tr>'
        )
    table = (
        "<table><thead><tr><th>Сотрудник</th><th>YouGile MCP</th>"
        f"<th>Статус</th><th></th></tr></thead><tbody>{''.join(rows)}</tbody></table>"
        if rows else '<p class="muted">Сотрудников пока нет.</p>'
    )
    return _shell(
        frame, "users", "Сотрудники",
        '<p class="hint">Подключение использует личный ключ сотрудника и его реальные '
        'права в YouGile. Отсюда можно отключить доступ или запретить новое '
        "подключение. Изменить права самого YouGile здесь нельзя.</p>" + table,
        done,
    )


def settings_page(frame: Frame) -> str:
    # Upstream company-settings visual shell retained. Only real settings
    # appear here; no decorative RBAC, role or Workflow controls.
    body = (
        "<h2>Настройки компании</h2>"
        '<p class="lead">Сведения о подключённой компании и правила доступа.</p>'
        "<table><tbody>"
        f"<tr><th>Компания</th><td>{e(frame.company_name)}</td></tr>"
        f"<tr><th>ID YouGile</th><td><code>{e(frame.company_id)}</code></td></tr>"
        f'<tr><th>Доступ</th><td>{"Активен" if frame.enabled else "Отключён"}</td></tr>'
        f"<tr><th>Сотрудники в списке</th><td>{frame.member_count}</td></tr>"
        f"<tr><th>Подключены</th><td>{frame.connected_count}</td></tr>"
        f"<tr><th>Подключение запрещено</th><td>{frame.blocked_count}</td></tr>"
        "</tbody></table>"
        '<p class="hint">Режим Full Access: каждый ассистент работает с правами '
        "соответствующей учётной записи YouGile, а не с правами владельца сервера.</p>"
        '<p class="hint">Отключение всей компании управляется владельцем '
        'облачного сервера. Индивидуальный доступ сотрудников можно изменить '
        'на вкладке «Сотрудники».</p>'
    )
    return _shell(frame, "settings", "Настройки компании", body)


def user_page(
    frame: Frame, person: Person, *, done: str | None = None,
    error: str | None = None,
) -> str:
    # Ported from Indalo's individual employee page with its live actions.
    action = _href(person)
    connected = (
        f'<p>Подключение к YouGile MCP: {_mcp_cell(person)}</p>'
        if person.connected else
        '<p class="muted">Активного подключения к YouGile MCP нет.</p>'
    )
    disconnect = (
        f'<form method="post" action="{action}/disconnect">{_csrf(frame.csrf)}'
        '<button class="inline danger" type="submit">Отключить от YouGile MCP</button>'
        "</form>"
        if person.connected else ""
    )
    if person.blocked:
        ban = (
            f'<form method="post" action="{action}/unblock">{_csrf(frame.csrf)}'
            '<button class="inline secondary" type="submit">Разрешить подключение</button>'
            "</form>"
        )
    elif person.yougile_admin:
        ban = ""  # An existing YouGile administrator can lift bans.
    else:
        ban = (
            f'<form method="post" action="{action}/block">{_csrf(frame.csrf)}'
            '<button class="inline danger" type="submit">Запретить подключение</button>'
            "</form>"
        )
    body = (
        f'<h2>{e(person.name)}</h2><p class="muted">{e(person.email)}</p>'
        + _pills(person) + connected
        + (f'<div class="error" role="alert">{e(error)}</div>' if error else "")
        + f'<p class="muted">ID сотрудника: <code>{e(person.id)}</code></p>'
        + f'<div class="actions">{disconnect}{ban}</div>'
        + (
            '<p class="hint">Подключение запрещено: войти в YouGile MCP '
            "сотрудник не сможет, пока запрет не снят.</p>"
            if person.blocked else
            '<p class="hint">Отключение удаляет персональный ключ MCP и '
            "завершает OAuth-сеансы. Пользователь может подключиться снова. "
            "Запрет дополнительно блокирует повторный вход.</p>"
        )
        + '<p><a href="/admin">Вернуться к сотрудникам</a></p>'
    )
    return _shell(frame, "users", person.name, body, done)
