"""Host-operator control plane, never inherited by company administrators.

Uses the existing Indalo-inspired admin pages and CSRF/session rules.
Only exact CLOUD_HOST_ADMIN_SUBJECTS identities authenticated live against
their own company YouGile are permitted to administer other tenants.
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

from contextlib import suppress
from urllib.parse import quote

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from . import admin_pages as ui
from .admin import AdminSession, CloudCompanyAdmin
from .yougile_signin import CloudSignInError


class CloudHostAdmin:
    """Bounded host operations without access to users' vendor API key text."""

    def __init__(self, company_admin: CloudCompanyAdmin):
        if not company_admin.host_admin_subjects:
            raise ValueError("Host operator allowlist required")
        self.admin = company_admin
        self.store = company_admin.store

    def routes(self) -> list[Route]:
        return [
            Route("/host", self.index, methods=["GET"]),
            Route("/host/companies/{company_id}", self.company, methods=["GET"]),
            Route("/host/companies/{company_id}/enable", self.enable, methods=["POST"]),
            Route("/host/companies/{company_id}/disable", self.disable, methods=["POST"]),
            Route(
                "/host/companies/{company_id}/members/{user_id}/disconnect",
                self.disconnect, methods=["POST"],
            ),
            Route(
                "/host/companies/{company_id}/members/{user_id}/block",
                self.block, methods=["POST"],
            ),
            Route(
                "/host/companies/{company_id}/members/{user_id}/unblock",
                self.unblock, methods=["POST"],
            ),
        ]

    async def _guard(
        self, request: Request, handler, *, post: bool = False,
    ) -> Response:
        async def authorized(req, actor, vendor, form):
            if not self.admin.is_host(actor):
                return self.admin._message(
                    "Доступ запрещён",
                    "Управление хостингом доступно только назначенному владельцу.",
                    403,
                )
            return await handler(req, actor, vendor, form)

        return await self.admin._guarded(request, authorized, post=post)

    async def index(self, request: Request) -> Response:
        return await self._guard(request, self._index)

    async def _index(self, request: Request, actor: AdminSession, vendor, form) -> Response:
        frame = await self.admin._frame(actor, [])
        companies = await self.store.host_companies()
        return self.admin._html(
            ui.host_companies_page(
                frame, companies, done=request.query_params.get("done"),
            )
        )

    async def company(self, request: Request) -> Response:
        return await self._guard(request, self._company)

    async def _company(self, request: Request, actor: AdminSession, vendor, form) -> Response:
        cid = request.path_params["company_id"]
        company = await self.store.get_company(cid)
        if company is None:
            return self.admin._message("Не найдено", "Компания отсутствует.", 404)
        accounts = {
            row["yougile_user_id"]: row
            for row in await self.store.company_members(cid)
        }
        blocked = await self.store.company_blocks(cid)
        people = []
        for uid in sorted(set(accounts) | blocked):
            row = accounts.get(uid)
            people.append(ui.Person(
                id=uid, name=(row["name"] if row else "") or uid,
                email=(row["email"] if row else "") or "",
                yougile_admin=bool(row["is_admin"]) if row else False,
                in_yougile=False, connected=row is not None,
                blocked=uid in blocked,
                last_connected=row["updated_at"] if row else None,
            ))
        frame = await self.admin._frame(actor, [])
        return self.admin._html(ui.host_company_page(
            frame, company, people, done=request.query_params.get("done"),
        ))

    async def _company_enabled(
        self, request: Request, actor: AdminSession, vendor, form,
        enabled: bool,
    ) -> Response:
        cid = request.path_params["company_id"]
        company = await self.store.get_company(cid)
        if company is None:
            return self.admin._message("Не найдено", "Компания отсутствует.", 404)
        if cid == actor.company_id:
            return self.admin._message(
                "Нельзя отключить", "Свою компанию владельца нельзя переключать здесь.",
                403,
            )
        await self.store.set_company_enabled(cid, enabled)
        await self.store.audit(
            "host_company_enabled" if enabled else "host_company_disabled",
            company_id=cid, user_id=int(actor.account_id),
        )
        return self.admin._redirect("/host?done=" + ("Включено" if enabled else "Отключено"))

    async def enable(self, request: Request) -> Response:
        return await self._guard(
            request,
            lambda req, act, vendor, form: self._company_enabled(
                req, act, vendor, form, True,
            ),
            post=True,
        )

    async def disable(self, request: Request) -> Response:
        return await self._guard(
            request,
            lambda req, act, vendor, form: self._company_enabled(
                req, act, vendor, form, False,
            ),
            post=True,
        )

    async def _member_action(
        self, request: Request, actor: AdminSession, vendor, form,
        operation: str,
    ) -> Response:
        cid = request.path_params["company_id"]
        vid = request.path_params["user_id"]
        company = await self.store.get_company(cid)
        if company is None:
            return self.admin._message("Не найдено", "Компания отсутствует.", 404)
        connected = await self.store.company_member(cid, vid)
        blocked = await self.store.is_member_blocked(cid, vid)
        if not connected and not blocked:
            return self.admin._message("Не найдено", "Пользователь не подключён.", 404)
        if cid == actor.company_id and vid == actor.vendor_user_id:
            return self.admin._message(
                "Нельзя изменить", "Владелец не может отключить собственный вход.", 403,
            )
        key = None
        if operation == "block":
            key = await self.store.block_member(
                cid, vid, actor_id=actor.company_id + ":" + actor.vendor_user_id,
            )
        elif operation == "unblock":
            if not blocked:
                return self.admin._message("Нет запрета", "Подключение не запрещено.", 404)
            await self.store.unblock_member(cid, vid)
        elif operation == "disconnect":
            if not connected:
                return self.admin._message("Нет подключения", "Пользователь не подключён.", 404)
            key = await self.store.disconnect_member(cid, vid)
        else:
            return self.admin._message("Неизвестное действие", "Попробуйте позже.", 400)
        await self.store.audit(
            "host_member_" + operation,
            company_id=cid, user_id=int(actor.account_id),
        )
        if key is not None:
            try:
                await self.admin.signin.revoke_key(key.reveal())
            except CloudSignInError:
                with suppress(Exception):
                    await self.store.audit(
                        "vendor_key_revocation_failed",
                        company_id=cid, user_id=int(actor.account_id),
                    )
        return self.admin._redirect(
            "/host/companies/" + quote(cid, safe="") + "?done=" + operation
        )

    async def block(self, request: Request) -> Response:
        return await self._guard(
            request,
            lambda req, a, v, f: self._member_action(req, a, v, f, "block"),
            post=True,
        )

    async def unblock(self, request: Request) -> Response:
        return await self._guard(
            request,
            lambda req, a, v, f: self._member_action(req, a, v, f, "unblock"),
            post=True,
        )

    async def disconnect(self, request: Request) -> Response:
        return await self._guard(
            request,
            lambda req, a, v, f: self._member_action(req, a, v, f, "disconnect"),
            post=True,
        )
