"""Company-owned administration using Indalo's existing admin UI conventions.

Adapted after indalo-tech/yougile-mcp-cloud/admin.py at ea88a0d5,
Copyright (c) Indalo, AGPL-3.0-only. Uses official SDK-native
YouGileClient and our own PostgreSQL/Valkey store, *not* upstream IAM.
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from contextlib import suppress
from dataclasses import dataclass, replace
from typing import Any
from urllib.parse import quote, urlparse

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.routing import Route

from ..api import ApiError, YouGileClient
from ..config import Secret, Settings
from . import admin_pages as ui
from . import pages
from .crypto import CloudCipher, hash_token
from .persistence import PostgresCloudStore
from .valkey import ValkeyCloudState
from .yougile_signin import (
    CloudBadCredentials, CloudSignInError, CloudYouGileSignIn,
    YouGileCompanyChoice,
)

_LOGIN_TTL = 600
_CHOICES_TTL = 300
_SESSION_TTL = 8 * 3600
_MAX_LOGIN_ATTEMPTS = 10

_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
        "frame-ancestors 'none'; base-uri 'none'"
    ),
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Cache-Control": "no-store",
}


@dataclass(frozen=True)
class AdminSession:
    """Actor identity loaded from trusted DB and rechecked in YouGile."""
    session_token: str
    company_id: str
    account_id: str
    vendor_user_id: str
    name: str


class CloudCompanyAdmin:
    """Server-rendered company administration, isolated by vendor company."""

    SESSION_COOKIE = "__Host-ygc-admin"
    LOGIN_COOKIE = "__Host-ygc-admin-login"

    def __init__(
        self, *, settings: Settings, signin: CloudYouGileSignIn,
        store: PostgresCloudStore, state: ValkeyCloudState,
        cipher: CloudCipher, csrf_secret: str, transport: Any = None,
    ):
        if not csrf_secret or len(csrf_secret) < 32 or not settings.public_url:
            raise ValueError("Secure company administration requires HTTPS and CSRF secret")
        self.settings = settings
        self.signin = signin
        self.store = store
        self.state = state
        self.cipher = cipher
        self.transport = transport
        self.origin = settings.public_url.rstrip("/")
        self._csrf_key = hmac.new(
            csrf_secret.encode("utf-8"), b"yougile-cloud/admin-csrf-v1", hashlib.sha256
        ).digest()

    def routes(self) -> list[Route]:
        return [
            Route("/admin", self.users, methods=["GET"]),
            Route("/admin/login", self.login_form, methods=["GET"]),
            Route("/admin/login", self.login, methods=["POST"]),
            Route("/admin/login/company", self.choose_company, methods=["POST"]),
            Route("/admin/logout", self.logout, methods=["POST"]),
            Route("/admin/settings", self.settings_form, methods=["GET"]),
            Route("/admin/users/{user_id}", self.user_form, methods=["GET"]),
            Route("/admin/users/{user_id}/disconnect", self.disconnect, methods=["POST"]),
            Route("/admin/users/{user_id}/block", self.block, methods=["POST"]),
            Route("/admin/users/{user_id}/unblock", self.unblock, methods=["POST"]),
        ]

    def _html(self, body: str, status: int = 200) -> HTMLResponse:
        return HTMLResponse(body, status_code=status, headers=_HEADERS)

    def _message(
        self, title: str, detail: str, status: int,
        *, relogin: bool = False,
    ) -> Response:
        link = ("/admin/login", "Войти заново") if relogin else None
        return self._html(pages.message_page(title, detail, link=link), status)

    def _redirect(self, path: str) -> RedirectResponse:
        return RedirectResponse(path, status_code=303, headers={"Cache-Control": "no-store"})

    def _set_cookie(self, response: Response, name: str, value: str, ttl: int) -> None:
        response.set_cookie(
            name, value, max_age=ttl, path="/", secure=True, httponly=True,
            samesite="lax",
        )

    def _clear_cookie(self, response: Response, name: str) -> None:
        response.delete_cookie(name, path="/", secure=True, httponly=True, samesite="lax")

    def _csrf(self, purpose: str, nonce: str) -> str:
        return hmac.new(
            self._csrf_key, f"{purpose}:{nonce}".encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def _origin_ok(self, request: Request) -> bool:
        host = urlparse(self.origin).netloc
        # Never trust host/origin from arbitrary forwarded headers.
        return (
            request.headers.get("host", "").lower() == host.lower()
            and request.headers.get("origin", self.origin) == self.origin
        )

    async def _form(self, request: Request) -> dict[str, str] | None:
        content_type = request.headers.get("content-type", "").lower()
        if not content_type.startswith("application/x-www-form-urlencoded"):
            return None
        size = request.headers.get("content-length")
        if size is not None and (not size.isdecimal() or int(size) > 8192):
            return None
        raw = await request.body()
        if len(raw) > 8192:
            return None
        data = await request.form()
        return {key: str(value) for key, value in data.multi_items()}

    def _post_valid(self, request: Request, form: dict, nonce: str, purpose: str) -> bool:
        token = form.get("csrf", "")
        return (
            self._origin_ok(request)
            and isinstance(token, str) and bool(nonce) and len(nonce) < 200
            and hmac.compare_digest(self._csrf(purpose, nonce), token)
        )

    async def _session(self, request: Request) -> AdminSession | None:
        token = request.cookies.get(self.SESSION_COOKIE, "")
        if not token or len(token) > 200:
            return None
        data = await self.state.get_json(self.state.key("admin-session", hash_token(token)))
        if not isinstance(data, dict):
            return None
        account_id = data.get("account_id")
        company_id = data.get("company_id")
        if not isinstance(account_id, str) or not isinstance(company_id, str):
            return None
        user = await self.store.get_user(account_id)
        account = await self.store.load(account_id)
        if (
            not user or not account or not user["enabled"]
            or not user["is_admin"] or account.company_id != company_id
            or user["company_id"] != company_id
        ):
            return None
        return AdminSession(
            session_token=token, company_id=company_id, account_id=account_id,
            vendor_user_id=user["yougile_user_id"],
            name=user["name"] or user["email"] or user["yougile_user_id"],
        )

    async def _invalidate(self, session: AdminSession) -> None:
        await self.state.client.delete(
            self.state.key("admin-session", hash_token(session.session_token))
        )

    async def _guarded(self, request: Request, handler, *, post: bool = False) -> Response:
        session = await self._session(request)
        if session is None:
            return self._redirect("/admin/login")
        form = None
        if post:
            form = await self._form(request)
            if form is None or not self._post_valid(
                request, form, session.session_token, "session",
            ):
                return self._message("Форма отклонена", "Обновите страницу и повторите.", 403)
        account = await self.store.load(session.account_id)
        if account is None:
            await self._invalidate(session)
            return self._redirect("/admin/login")
        cfg = replace(
            self.settings, company_id=session.company_id, yougile_api_key=account.api_key,
        )
        try:
            async with YouGileClient(cfg, transport=self.transport) as client:
                company = await client.request("CompanyController_get")
                me = await client.request("UserController_getMe")
                if (
                    not isinstance(company.data, dict)
                    or company.data.get("id") != session.company_id
                    or not isinstance(me.data, dict)
                    or me.data.get("id") != session.vendor_user_id
                    or me.data.get("isAdmin") is not True
                ):
                    await self._invalidate(session)
                    return self._message(
                        "Нет прав администратора",
                        "YouGile больше не подтверждает права администратора компании.",
                        403, relogin=True,
                    )
                return await handler(
                    request, session, client, form,
                )
        except ApiError as exc:
            if exc.status_code in (401, 403):
                await self._invalidate(session)
                return self._message(
                    "Доступ прекращён", "YouGile больше не принимает ваш ключ.",
                    403, relogin=True,
                )
            return self._message("YouGile недоступен", "Попробуйте позже.", 502)

    async def _people(self, session: AdminSession, client: YouGileClient) -> list[ui.Person]:
        live = await client.list_all(
            "UserController_search",
            query={"limit": 1000}, max_pages=10, max_items=5000,
        )
        connected = {
            row["yougile_user_id"]: row
            for row in await self.store.company_members(session.company_id)
        }
        denied = await self.store.company_blocks(session.company_id)
        people = {}
        for user in live:
            uid = user.get("id")
            if not isinstance(uid, str) or not uid:
                continue
            row = connected.get(uid)
            people[uid] = ui.Person(
                id=uid, name=user.get("realName") or user.get("email") or uid,
                email=user.get("email") or "", yougile_admin=bool(user.get("isAdmin")),
                in_yougile=True, connected=row is not None,
                blocked=uid in denied,
                last_connected=row["updated_at"] if row else None,
            )
        for uid in sorted(set(connected) | denied):
            if uid in people:
                continue
            row = connected.get(uid)
            people[uid] = ui.Person(
                id=uid, name=(row["name"] if row else "") or uid,
                email=(row["email"] if row else "") or "",
                yougile_admin=bool(row["is_admin"]) if row else False,
                in_yougile=False, connected=row is not None,
                blocked=uid in denied,
                last_connected=row["updated_at"] if row else None,
            )
        return sorted(people.values(), key=lambda p: (p.name.casefold(), p.id))

    async def _frame(self, session: AdminSession, people: list[ui.Person]) -> ui.Frame:
        company = await self.store.get_company(session.company_id)
        if not company or not company["enabled"]:
            raise ValueError("Company no longer available")
        return ui.Frame(
            company_id=session.company_id, company_name=company["name"],
            enabled=company["enabled"], admin_name=session.name,
            csrf=self._csrf("session", session.session_token),
            member_count=len(people),
            connected_count=sum(p.connected for p in people),
            blocked_count=sum(p.blocked for p in people),
        )

    def _login_page(
        self, nonce: str, *, error: str | None = None,
        login: str = "", status: int = 200,
    ) -> Response:
        return self._html(pages.login_page(
            action="/admin/login",
            hidden={"csrf": self._csrf("login", nonce)},
            heading="Администрирование YouGile MCP",
            lead="Войти может только администратор компании YouGile.",
            error=error, login=login,
        ), status)

    async def login_form(self, request: Request) -> Response:
        if await self._session(request):
            return self._redirect("/admin")
        nonce = secrets.token_urlsafe(32)
        response = self._login_page(nonce)
        self._set_cookie(response, self.LOGIN_COOKIE, nonce, _LOGIN_TTL)
        return response

    async def login(self, request: Request) -> Response:
        form = await self._form(request)
        nonce = request.cookies.get(self.LOGIN_COOKIE, "")
        if form is None or not self._post_valid(request, form, nonce, "login"):
            return self._message(
                "Форма отклонена", "Откройте страницу входа заново.", 403, relogin=True,
            )
        login = form.get("login", "").strip()
        password = form.get("password", "")
        if not login or not password or len(login) > 320 or len(password) > 1024:
            return self._login_page(nonce, error="Введите логин и пароль.", status=400)
        bucket = self.state.key(
            "admin-login-attempt",
            hash_token((request.client.host if request.client else "?") + ":" + login.lower()),
        )
        if await self.state.count_failure(bucket, window_seconds=900) > _MAX_LOGIN_ATTEMPTS:
            return self._login_page(nonce, error="Слишком много попыток.", status=429)
        try:
            choices = [c for c in await self.signin.companies(login, password) if c.is_admin]
        except CloudBadCredentials:
            return self._login_page(nonce, error="Неверный логин или пароль.", status=401)
        except CloudSignInError:
            return self._message("YouGile недоступен", "Попробуйте позже.", 502)
        if not choices:
            return self._login_page(
                nonce, error="Для этой учётной записи нет компаний с правами администратора.",
                status=403,
            )
        if len(choices) == 1:
            return await self._finish(nonce, login, password, choices[0])
        encrypted = self.cipher.encrypt(
            Secret(
                json.dumps({
                    "login": login, "password": password,
                    "companies": [[c.id, c.name, c.is_admin] for c in choices],
                }, ensure_ascii=False),
            ),
        )
        await self.state.put_bytes(
            self.state.key("admin-choice", hash_token(nonce)), encrypted,
            ttl=_CHOICES_TTL,
        )
        return self._html(pages.company_page(
            action="/admin/login/company",
            hidden={"csrf": self._csrf("choose", nonce)},
            companies=[(c.id, c.name) for c in choices],
            lead="Вы администратор нескольких компаний. Выберите, какой управлять.",
        ))

    async def choose_company(self, request: Request) -> Response:
        form = await self._form(request)
        nonce = request.cookies.get(self.LOGIN_COOKIE, "")
        if form is None or not self._post_valid(request, form, nonce, "choose"):
            return self._message(
                "Форма отклонена", "Откройте страницу входа заново.", 403, relogin=True,
            )
        encrypted = await self.state.take_bytes(
            self.state.key("admin-choice", hash_token(nonce))
        )
        if encrypted is None:
            return self._message("Время вышло", "Войдите заново.", 400, relogin=True)
        try:
            data = json.loads(self.cipher.decrypt(encrypted).reveal())
            valid = [c for c in data["companies"] if c[0] == form.get("company")]
            if len(valid) != 1:
                return self._message("Компания недоступна", "Войдите заново.", 403)
            return await self._finish(
                nonce, data["login"], data["password"], YouGileCompanyChoice(*valid[0]),
            )
        except (ValueError, KeyError, TypeError, IndexError):
            return self._message("Время вышло", "Войдите заново.", 400, relogin=True)

    async def _finish(
        self, nonce: str, login: str, password: str, company: YouGileCompanyChoice,
    ) -> Response:
        try:
            person = await self.signin.provision(
                login, password, selected_company_id=company.id,
            )
        except CloudBadCredentials:
            return self._login_page(
                nonce, error="Неверный логин или пароль.", status=401,
            )
        except CloudSignInError:
            return self._message("YouGile недоступен", "Не удалось подключиться.", 502)
        if not company.is_admin or not person.is_admin:
            with suppress(Exception):
                await self.signin.revoke_key(person.api_key.reveal())
            return self._message(
                "Нет прав администратора",
                "Вы не администратор выбранной компании YouGile.", 403,
            )
        try:
            saved = await self.store.save_account(person, company_name=company.name)
        except Exception:
            with suppress(Exception):
                await self.signin.revoke_key(person.api_key.reveal())
            return self._message(
                "Подключение отклонено",
                "Компания или пользователь недоступны, либо хранилище не отвечает.", 403,
            )
        session_token = secrets.token_urlsafe(48)
        try:
            await self.state.put_json(
                self.state.key("admin-session", hash_token(session_token)),
                {"account_id": saved.account_id, "company_id": company.id},
                ttl=_SESSION_TTL, once=True,
            )
        except Exception:
            return self._message("Сессия недоступна", "Попробуйте позже.", 503)
        if saved.previous_api_key is not None:
            try:
                await self.signin.revoke_key(saved.previous_api_key.reveal())
            except CloudSignInError:
                with suppress(Exception):
                    await self.store.audit(
                        "old_vendor_key_revocation_failed",
                        company_id=company.id, user_id=int(saved.account_id),
                    )
        response = self._redirect("/admin")
        self._set_cookie(response, self.SESSION_COOKIE, session_token, _SESSION_TTL)
        self._clear_cookie(response, self.LOGIN_COOKIE)
        return response

    async def logout(self, request: Request) -> Response:
        session = await self._session(request)
        form = await self._form(request)
        if (
            session is None or form is None
            or not self._post_valid(request, form, session.session_token, "session")
        ):
            return self._message("Форма отклонена", "Откройте страницу заново.", 403)
        await self._invalidate(session)
        response = self._redirect("/admin/login")
        self._clear_cookie(response, self.SESSION_COOKIE)
        return response

    async def users(self, request: Request) -> Response:
        return await self._guarded(request, self._users)

    async def _users(
        self, request: Request, session: AdminSession,
        client: YouGileClient, form: dict | None,
    ) -> Response:
        people = await self._people(session, client)
        frame = await self._frame(session, people)
        return self._html(ui.users_page(frame, people, request.query_params.get("done")))

    async def settings_form(self, request: Request) -> Response:
        return await self._guarded(request, self._settings)

    async def _settings(
        self, request: Request, session: AdminSession,
        client: YouGileClient, form: dict | None,
    ) -> Response:
        people = await self._people(session, client)
        return self._html(ui.settings_page(await self._frame(session, people)))

    async def user_form(self, request: Request) -> Response:
        return await self._guarded(request, self._user)

    async def _user(
        self, request: Request, session: AdminSession,
        client: YouGileClient, form: dict | None,
    ) -> Response:
        people = await self._people(session, client)
        person = next(
            (p for p in people if p.id == request.path_params["user_id"]), None
        )
        if person is None:
            return self._message("Не найдено", "Сотрудника нет в компании.", 404)
        frame = await self._frame(session, people)
        return self._html(ui.user_page(
            frame, person, done=request.query_params.get("done"),
        ))

    async def _change(
        self, request: Request, session: AdminSession,
        client: YouGileClient, form: dict | None, action: str,
    ) -> Response:
        target = request.path_params["user_id"]
        people = await self._people(session, client)
        person = next((p for p in people if p.id == target), None)
        if person is None:
            return self._message("Не найдено", "Сотрудника нет в компании.", 404)
        if action == "block" and (
            target == session.vendor_user_id or person.yougile_admin
        ):
            return self._message(
                "Нельзя запретить", "Администратора YouGile нельзя блокировать здесь.", 403,
            )
        if action == "disconnect":
            key = await self.store.disconnect_member(session.company_id, target)
            if key is None:
                return self._message("Нет подключения", "Сотрудник не подключён.", 404)
        elif action == "block":
            key = await self.store.block_member(
                session.company_id, target, actor_id=session.vendor_user_id,
            )
        elif action == "unblock":
            await self.store.unblock_member(session.company_id, target)
            key = None
        else:
            return self._message("Неизвестное действие", "Попробуйте снова.", 400)
        await self.store.audit(
            "admin_" + action,
            company_id=session.company_id, user_id=int(session.account_id),
        )
        if key is not None:
            try:
                await self.signin.revoke_key(key.reveal())
            except CloudSignInError:
                with suppress(Exception):
                    await self.store.audit(
                        "vendor_key_revocation_failed",
                        company_id=session.company_id, user_id=int(session.account_id),
                    )
        if target == session.vendor_user_id and action == "disconnect":
            await self._invalidate(session)
            response = self._redirect("/admin/login")
            self._clear_cookie(response, self.SESSION_COOKIE)
            return response
        return self._redirect(
            f"/admin/users/{quote(target, safe='')}?done={action}"
        )

    async def disconnect(self, request: Request) -> Response:
        return await self._guarded(
            request,
            lambda req, ses, cli, frm: self._change(req, ses, cli, frm, "disconnect"),
            post=True,
        )

    async def block(self, request: Request) -> Response:
        return await self._guarded(
            request,
            lambda req, ses, cli, frm: self._change(req, ses, cli, frm, "block"),
            post=True,
        )

    async def unblock(self, request: Request) -> Response:
        return await self._guarded(
            request,
            lambda req, ses, cli, frm: self._change(req, ses, cli, frm, "unblock"),
            post=True,
        )
