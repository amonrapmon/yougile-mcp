"""Authenticated Streamable HTTP MCP and Indalo's YouGile sign-in screens.

The OAuth endpoints and protected /mcp come from the official MCP SDK v2.
The sign-in form, company choice and request guards follow Indalo's
yougile-mcp-cloud/web.py (commit ea88a0d5, © Indalo, AGPL-3.0-only).
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from contextlib import suppress
from urllib.parse import urlparse
from typing import Any

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import (
    AuthSettings,
    ClientRegistrationOptions,
    RevocationOptions,
)
from mcp.server.transport_security import (
    RequestBodyLimitMiddleware,
    TransportSecuritySettings,
)
from pydantic import AnyHttpUrl
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from ..config import Secret, Settings
from ..mcp.cloud import CloudTenantSessions, VerifiedCloudActor, make_cloud_mcp_server
from . import pages, redirects
from .admin import CloudCompanyAdmin
from .host_admin import CloudHostAdmin
from .crypto import CloudCipher, hash_token
from .oauth import CloudOAuthProvider
from .persistence import PostgresCloudStore
from .valkey import ValkeyCloudState
from .yougile_signin import (
    CloudBadCredentials,
    CloudSignInError,
    CloudYouGileSignIn,
    YouGileCompanyChoice,
)

_CRED_TTL = 300
_MAX_LOGIN_ATTEMPTS = 10
_SCOPE = "yougile.full"

# Only stage labels and short SHA-256 fingerprints of random OAuth flow IDs.
# No passwords, OAuth codes, refresh tokens, client identity or company data.
_LOG = logging.getLogger("uvicorn.error")

_SECURITY = {
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'unsafe-inline'; script-src 'self'; img-src https://avatars.githubusercontent.com; form-action 'self'; "
        "frame-ancestors 'none'; base-uri 'none'"
    ),
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Cache-Control": "no-store",
}


def _html(text: str, status: int = 200) -> HTMLResponse:
    return HTMLResponse(text, status_code=status, headers=_SECURITY)


class CloudLoginPages:
    """HTTP forms are never an authorization source without an OAuth flow."""

    def __init__(
        self, *, provider: CloudOAuthProvider, signin: CloudYouGileSignIn,
        state: ValkeyCloudState, store: PostgresCloudStore,
        cipher: CloudCipher, csrf_secret: str,
    ):
        if not csrf_secret or len(csrf_secret) < 32:
            raise ValueError("A high entropy CSRF secret is required")
        self.provider = provider
        self.signin = signin
        self.state = state
        self.store = store
        self.cipher = cipher
        self._csrf_key = hmac.new(
            csrf_secret.encode(), b"yougile-cloud/form-csrf-v1", hashlib.sha256
        ).digest()

    def _trace(self, stage: str, flow: str) -> None:
        _LOG.info("oauth_flow stage=%s flow_ref=%s", stage, hash_token(flow)[:12] if flow else "none")

    def _csrf(self, prefix: str, flow: str) -> str:
        return hmac.new(self._csrf_key, f"{prefix}:{flow}".encode(), hashlib.sha256).hexdigest()

    def _origin_ok(self, request: Request) -> bool:
        # Do not trust X-Forwarded-Host/Proto forwarded by arbitrary peers.
        # The reverse proxy must preserve the public Host and strip hostile
        # forwarded headers; only the pinned public origin may submit forms.
        expected = urlparse(self.provider.public_url)
        if request.headers.get("host", "").lower() != expected.netloc.lower():
            return False
        origin = request.headers.get("origin")
        return origin is None or origin == self.provider.public_url

    def _post_valid(self, request: Request, fields: dict, purpose: str, flow: str) -> bool:
        expected = self._csrf(purpose, flow)
        supplied = fields.get("csrf", "")
        return (
            self._origin_ok(request)
            and bool(flow)
            and len(flow) <= 200
            and isinstance(supplied, str)
            and hmac.compare_digest(expected, supplied)
        )

    async def _read_form(self, request: Request) -> dict[str, str] | None:
        if not request.headers.get("content-type", "").lower().startswith(
            "application/x-www-form-urlencoded"
        ):
            return None
        size = request.headers.get("content-length")
        if size is not None and (not size.isdecimal() or int(size) > 8192):
            return None
        raw = await request.body()
        if len(raw) > 8192:
            return None
        form = await request.form()
        return {key: str(value) for key, value in form.multi_items()}

    def _form(
        self, flow: str, authreq: dict, *, error: str | None = None,
        login: str = "", status: int = 200,
    ) -> HTMLResponse:
        return _html(
            pages.login_page(
                action="/signin",
                hidden={"flow": flow, "csrf": self._csrf("signin", flow)},
                heading="Вход в YouGile MCP",
                lead="Войдите под своей учётной записью YouGile.",
                error=error, login=login,
                client=(
                    authreq.get("client_name", ""),
                    redirects.destination(authreq.get("redirect_uri", "")),
                ),
            ),
            status,
        )

    async def home(self, request: Request) -> Response:
        return _html(pages.home_page(self.provider.mcp_url))

    async def landing_script(self, request: Request) -> Response:
        # Static, public copy handler. OAuth forms never load JavaScript.
        return Response(
            pages.LANDING_COPY_JS,
            media_type="application/javascript",
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )

    async def health(self, request: Request) -> Response:
        # Liveness, not database status or deployment secrets.
        return JSONResponse({"ok": True}, headers={"Cache-Control": "no-store"})

    async def show(self, request: Request) -> Response:
        flow = request.query_params.get("flow", "")
        authreq = await self.provider.pending_request(flow)
        self._trace("signin_get_valid" if authreq is not None else "signin_get_missing", flow)
        if authreq is None:
            return _html(pages.message_page(
                "Ссылка устарела", "Начните подключение заново в AI-клиенте."
            ), 400)
        return self._form(flow, authreq)

    async def submit(self, request: Request) -> Response:
        fields = await self._read_form(request)
        if fields is None:
            return _html(pages.message_page("Некорректная форма", "Попробуйте снова."), 400)
        flow = fields.get("flow", "")
        if not self._post_valid(request, fields, "signin", flow):
            return _html(pages.message_page("Форма отклонена", "Начните подключение заново."), 403)
        authreq = await self.provider.pending_request(flow)
        if authreq is None:
            return _html(pages.message_page("Ссылка устарела", "Начните подключение заново."), 400)
        login = fields.get("login", "").strip()
        password = fields.get("password", "")
        if not login or not password or len(login) > 320 or len(password) > 1024:
            return self._form(flow, authreq, error="Введите корректный логин и пароль.", status=400)
        bucket = self.state.key(
            "login-attempt", hash_token((request.client.host if request.client else "?") + ":" + login.lower())
        )
        if await self.state.failures(bucket) >= _MAX_LOGIN_ATTEMPTS:
            return self._form(flow, authreq, error="Слишком много попыток. Повторите позже.", status=429)
        # Count every attempt atomically before sending credentials to YouGile.
        if await self.state.count_failure(bucket, window_seconds=900) > _MAX_LOGIN_ATTEMPTS:
            return self._form(flow, authreq, error="Слишком много попыток. Повторите позже.", status=429)
        try:
            companies = await self.signin.companies(login, password)
        except CloudBadCredentials:
            return self._form(flow, authreq, error="Неверный логин или пароль.", login=login, status=401)
        except CloudSignInError:
            return self._form(flow, authreq, error="YouGile временно недоступен.", status=502)
        if not companies:
            return self._form(flow, authreq, error="Нет доступных компаний YouGile.", status=403)
        if len(companies) == 1:
            return await self._finish(flow, login, password, companies[0])
        # Password is kept only for a brief company-choice step, encrypted.
        temporary = json.dumps({
            "login": login, "password": password,
            "companies": [[c.id, c.name, c.is_admin] for c in companies],
        }, ensure_ascii=False)
        await self.state.put_bytes(
            self.state.key("temporary-credentials", hash_token(flow)),
            self.cipher.encrypt(Secret(temporary)), ttl=_CRED_TTL,
        )
        self._trace("company_choice_rendered", flow)
        return _html(pages.company_page(
            action="/signin/company",
            hidden={"flow": flow, "csrf": self._csrf("company", flow)},
            companies=[(c.id, c.name) for c in companies],
        ))

    async def choose_company(self, request: Request) -> Response:
        fields = await self._read_form(request)
        if fields is None:
            self._trace("company_post_invalid_form", "")
            return _html(pages.message_page("Некорректная форма", "Попробуйте снова."), 400)
        flow = fields.get("flow", "")
        self._trace("company_post_received", flow)
        if not self._post_valid(request, fields, "company", flow):
            self._trace("company_post_invalid_csrf", flow)
            return _html(pages.message_page("Форма отклонена", "Начните подключение заново."), 403)
        if await self.provider.pending_request(flow) is None:
            self._trace("company_post_missing_oauth_request", flow)
            return _html(pages.message_page("Ссылка устарела", "Начните подключение заново."), 400)
        encrypted = await self.state.take_bytes(
            self.state.key("temporary-credentials", hash_token(flow))
        )
        if encrypted is None:
            self._trace("company_post_missing_credentials", flow)
            return _html(pages.message_page("Время вышло", "Начните подключение заново."), 400)
        self._trace("company_post_claimed_credentials", flow)
        try:
            data = json.loads(self.cipher.decrypt(encrypted).reveal())
            requested = fields.get("company", "")
            choices = [
                YouGileCompanyChoice(id=c[0], name=c[1], is_admin=c[2])
                for c in data["companies"] if c[0] == requested
            ]
            if len(choices) != 1:
                self._trace("company_post_invalid_selection", flow)
                return _html(pages.message_page("Компания недоступна", "Начните заново."), 403)
            return await self._finish(flow, data["login"], data["password"], choices[0])
        except (ValueError, KeyError, TypeError, IndexError):
            self._trace("company_post_invalid_temporary_state", flow)
            return _html(pages.message_page("Время вышло", "Начните подключение заново."), 400)

    async def _finish(
        self, flow: str, login: str, password: str, company: YouGileCompanyChoice,
    ) -> Response:
        try:
            account = await self.signin.provision(
                login, password, selected_company_id=company.id,
            )
        except CloudBadCredentials:
            return _html(pages.message_page(
                "Неверный логин или пароль", "Начните подключение заново."
            ), 401)
        except CloudSignInError:
            return _html(pages.message_page(
                "Ошибка подключения", "Не удалось получить ключ YouGile."
            ), 502)
        self._trace("vendor_account_provisioned", flow)
        try:
            saved = await self.store.save_account(account, company_name=company.name)
        except Exception:
            # We have issued a new key but did not commit it. Avoid orphan keys.
            with suppress(Exception):
                await self.signin.revoke_key(account.api_key.reveal())
            return _html(pages.message_page(
                "Ошибка сохранения", "Подключение не завершено. Повторите позже."
            ), 503)
        self._trace("cloud_account_saved", flow)
        try:
            destination = await self.provider.finish_signin(
                flow, account_id=saved.account_id,
            )
        except Exception:
            self._trace("oauth_completion_failed", flow)
            # This account is persisted; do NOT revoke its current key here.
            return _html(pages.message_page(
                "Ошибка OAuth", "Начните подключение заново."
            ), 503)
        self._trace("oauth_redirect_issued", flow)
        # Old vendor key has been replaced in the DB transaction, and is no
        # longer needed. Failed vendor revoke must be audited for remediation.
        if saved.previous_api_key is not None:
            try:
                await self.signin.revoke_key(saved.previous_api_key.reveal())
            except CloudSignInError:
                with suppress(Exception):
                    await self.store.audit(
                        "old_vendor_key_revocation_failed",
                        company_id=account.company_id,
                        user_id=int(saved.account_id),
                    )
        return RedirectResponse(
            destination, status_code=302, headers={"Cache-Control": "no-store"},
        )


def make_cloud_http_app(
    *, settings: Settings, provider: CloudOAuthProvider,
    signin: CloudYouGileSignIn, store: PostgresCloudStore,
    state: ValkeyCloudState, cipher: CloudCipher, csrf_secret: str,
    yougile_transport: Any = None,
    host_admin_subjects: tuple[str, ...] = (),
):
    """Mount OAuth, safe forms and auth-required /mcp in a single SDK ASGI app.

    Returns an ASGI application. Does not open a socket.
    """
    if (
        settings.company_id is not None or settings.has_api_key
        or settings.auth_mode != "required"
        or settings.public_url != provider.public_url
    ):
        raise ValueError("Hosted HTTP requires per-user keys and verified HTTPS origin")
    pages_handler = CloudLoginPages(
        provider=provider, signin=signin, state=state,
        store=store, cipher=cipher, csrf_secret=csrf_secret,
    )
    company_admin = CloudCompanyAdmin(
        settings=settings, signin=signin, store=store, state=state,
        cipher=cipher, csrf_secret=csrf_secret, transport=yougile_transport,
        host_admin_subjects=host_admin_subjects,
    )

    async def actor(_context):
        token = get_access_token()  # populated by official SDK Bearer middleware
        if (
            token is None or token.resource != provider.mcp_url
            or token.subject is None or _SCOPE not in token.scopes
        ):
            return None
        return VerifiedCloudActor(token.subject)

    sessions = CloudTenantSessions(
        settings, resolve_actor=actor, accounts=store,
        transport=yougile_transport,
    )
    server = make_cloud_mcp_server(sessions)
    auth = AuthSettings(
        issuer_url=AnyHttpUrl(provider.public_url),
        resource_server_url=AnyHttpUrl(provider.mcp_url),
        validate_token_resource=True,
        required_scopes=[_SCOPE],
        client_registration_options=ClientRegistrationOptions(
            enabled=True, valid_scopes=[_SCOPE], default_scopes=[_SCOPE],
        ),
        revocation_options=RevocationOptions(enabled=True),
    )
    parsed = urlparse(provider.public_url)
    app = server.streamable_http_app(
        streamable_http_path="/mcp", json_response=True,
        stateless_http=True, auth=auth,
        token_verifier=provider, auth_server_provider=provider,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[parsed.netloc],
            allowed_origins=[provider.public_url],
        ),
        custom_starlette_routes=[
            Route("/", pages_handler.home, methods=["GET"]),
            Route("/assets/landing.js", pages_handler.landing_script, methods=["GET"]),
            Route("/healthz", pages_handler.health, methods=["GET"]),
            Route("/signin", pages_handler.show, methods=["GET"]),
            Route("/signin", pages_handler.submit, methods=["POST"]),
            Route("/signin/company", pages_handler.choose_company, methods=["POST"]),
            *company_admin.routes(),
            *(CloudHostAdmin(company_admin).routes() if host_admin_subjects else []),
        ],
    )
    app.add_middleware(RequestBodyLimitMiddleware, max_body_size=4 * 1024 * 1024)
    return app
