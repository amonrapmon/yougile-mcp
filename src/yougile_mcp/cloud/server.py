"""Private network runner for the opt-in hosted OAuth MCP.

TLS termination and public routing must be provided separately by a
trusted reverse proxy after deployment review. A guarded container-only
0.0.0.0 bind is allowed when Docker does not publish any application ports.
SPDX-License-Identifier: AGPL-3.0-only
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

from ..config import ConfigError, Settings
from . import redirects
from .crypto import CloudCipher
from .oauth import CloudOAuthProvider
from .persistence import PostgresCloudStore
from .valkey import ValkeyCloudState
from .web import make_cloud_http_app
from .yougile_signin import CloudYouGileSignIn


async def cloud_serve(
    settings: Settings, *, env: Mapping[str, str] | None = None,
) -> None:
    values = os.environ if env is None else env
    # In Docker the service must listen on its container interface for the
    # reverse proxy to reach it. This is NOT permission to publish port 8000
    # on the host: the deployment Compose deliberately contains no ports.
    # Outside Docker, only a loopback bind is acceptable.
    private_container_bind = (
        settings.host == "0.0.0.0"
        and values.get("CLOUD_PRIVATE_CONTAINER_BIND") == "1"
        and Path("/.dockerenv").exists()
    )
    if (
        settings.transport != "http"
        or (
            settings.host not in {"127.0.0.1", "::1", "localhost"}
            and not private_container_bind
        )
        or settings.company_id is not None
        or settings.has_api_key
        or not settings.public_url
    ):
        raise ConfigError(
            "Hosted OAuth requires a loopback bind or explicitly guarded "
            "private Docker bind, HTTPS MCP_PUBLIC_URL and no global YouGile key"
        )
    db_url = values.get("CLOUD_DATABASE_URL", "")
    valkey_url = values.get("CLOUD_VALKEY_URL", "")
    jwt_secret = values.get("CLOUD_JWT_SECRET", "")
    enc_keys = [
        item.strip() for item in values.get("CLOUD_ENCRYPTION_KEYS", "").split(",")
        if item.strip()
    ]
    if not db_url or not valkey_url or len(jwt_secret) < 32 or not enc_keys:
        raise ConfigError(
            "CLOUD_DATABASE_URL, CLOUD_VALKEY_URL, CLOUD_JWT_SECRET (32+ chars) "
            "and CLOUD_ENCRYPTION_KEYS are required"
        )
    try:
        cipher = CloudCipher(enc_keys)
        store = PostgresCloudStore(db_url, cipher)
        await store.open()
        try:
            await store.migrate()
            state = await ValkeyCloudState.connect(valkey_url)
            try:
                oauth = CloudOAuthProvider(
                    public_url=settings.public_url, store=store,
                    state=state, jwt_secret=jwt_secret,
                    redirect_origins=redirects.parse_allowed(
                        values.get("CLOUD_OAUTH_REDIRECT_ORIGINS", ""),
                    ),
                )
                raw_host = values.get("CLOUD_HOST_ADMIN_SUBJECTS", "")
                host_subjects = tuple(
                    s.strip() for s in raw_host.split(",") if s.strip()
                )
                for subject in host_subjects:
                    company, delimiter, vendor_user = subject.partition(":")
                    if (
                        not delimiter or not company or not vendor_user
                        or ":" in vendor_user or any(c.isspace() for c in subject)
                    ):
                        raise ConfigError(
                            "CLOUD_HOST_ADMIN_SUBJECTS must contain exact "
                            "companyId:yougileUserId pairs"
                        )
                app = make_cloud_http_app(
                    settings=settings, provider=oauth, store=store,
                    state=state, cipher=cipher, csrf_secret=jwt_secret,
                    signin=CloudYouGileSignIn(settings),
                    host_admin_subjects=host_subjects,
                )
                import uvicorn

                server = uvicorn.Server(
                    uvicorn.Config(
                        app, host=settings.host, port=settings.port,
                        proxy_headers=False, access_log=False,
                        log_level="info",
                    )
                )
                await server.serve()
            finally:
                await state.close()
        finally:
            await store.close()
    except ValueError:
        # Do not print exception details, which may contain connection data.
        raise ConfigError("Cloud OAuth configuration rejected") from None
