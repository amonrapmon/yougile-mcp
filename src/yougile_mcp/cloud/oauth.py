"""OAuth 2.1 provider over the official MCP Python SDK v2.

Adapted from Indalo yougile-mcp-cloud/oauth.py (commit ea88a0d5).
Copyright (c) Indalo, AGPL-3.0-only. Our SDK-based provider uses the
same flow, PKCE, one-use codes, rotation and revocation, with PyJWT
signature validation and separate per-account YouGile keys.
SPDX-License-Identifier: AGPL-3.0-only
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import jwt
from mcp.server.auth.provider import (
    AccessToken, AuthorizationCode, AuthorizationParams, AuthorizeError,
    RefreshToken, RegistrationError, TokenError, construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from jwt.exceptions import InvalidTokenError

from ..cloud import redirects
from ..cloud.crypto import hash_token, new_opaque_token
from ..cloud.persistence import PostgresCloudStore
from ..cloud.valkey import ValkeyCloudState

AUTH_REQUEST_TTL = 15 * 60
AUTH_CODE_TTL = 5 * 60
ACCESS_TOKEN_TTL = 3600
REFRESH_TOKEN_TTL = 30 * 24 * 3600
_SCOPE = "yougile.full"
_LOG = logging.getLogger("uvicorn.error")


class CloudOAuthProvider:
    """Authorized user IDs come ONLY from successful YouGile sign-in.

    This class never accepts an account ID from an MCP tool request. PKCE S256,
    client-redirect and authorization-code checks are performed by the
    official MCP SDK's OAuth route handlers.
    """

    def __init__(
        self, *, public_url: str, store: PostgresCloudStore,
        state: ValkeyCloudState, jwt_secret: str,
        redirect_origins: tuple[str, ...] = (),
    ):
        parsed = urlparse(public_url)
        if (
            parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/")
        ):
            raise ValueError("OAuth public URL must be a trusted HTTPS origin")
        if not isinstance(jwt_secret, str) or len(jwt_secret) < 32:
            raise ValueError("High-entropy JWT signing key required")
        if store is None or state is None:
            raise ValueError("Durable OAuth backends required")
        self.public_url = public_url.rstrip("/")
        self.mcp_url = self.public_url + "/mcp"
        self.store = store
        self.state = state
        self.redirect_origins = redirect_origins
        self._signing_key = hmac.new(
            jwt_secret.encode("utf-8"), b"yougile-cloud/mcp-access-v1", hashlib.sha256
        ).digest()

    def _state_key(self, prefix: str, token: str) -> str:
        return self.state.key(prefix, hash_token(token))

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        item = await self.store.get_oauth_client(client_id)
        return OAuthClientInformationFull.model_validate(item) if item else None

    async def register_client(self, info: OAuthClientInformationFull) -> None:
        if not info.client_id or not info.redirect_uris or any(
            not redirects.allowed(str(uri), self.redirect_origins)
            for uri in info.redirect_uris
        ):
            raise RegistrationError(
                error="invalid_redirect_uri",
                error_description="Only approved AI callbacks or local native clients are allowed",
            )
        await self.store.save_oauth_client(
            info.client_id, info.model_dump(mode="json", exclude_none=True),
        )

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams,
    ) -> str:
        redirect = str(params.redirect_uri)
        if not redirects.allowed(redirect, self.redirect_origins):
            raise AuthorizeError(
                error="invalid_request", error_description="Redirect URI not allowed",
            )
        if params.resource is not None and params.resource.rstrip("/") != self.mcp_url:
            raise AuthorizeError(
                error="invalid_target", error_description="Unknown MCP resource",
            )
        requested = list(params.scopes or [_SCOPE])
        if any(scope != _SCOPE for scope in requested):
            raise AuthorizeError(
                error="invalid_scope", error_description="Unsupported OAuth scope",
            )
        flow = new_opaque_token()
        ok = await self.state.put_json(
            self._state_key("authreq", flow),
            {
                "client_id": client.client_id,
                "client_name": client.client_name or "",
                "redirect_uri": redirect,
                "redirect_uri_provided_explicitly": params.redirect_uri_provided_explicitly,
                "code_challenge": params.code_challenge,
                "scopes": requested,
                "state": params.state,
                "resource": self.mcp_url,
            },
            ttl=AUTH_REQUEST_TTL, once=True,
        )
        if not ok:
            raise AuthorizeError(error="server_error", error_description="Unable to open login")
        # Correlation only: never log the raw flow token, client ID or redirect URI.
        _LOG.info("oauth_flow stage=authorization_created flow_ref=%s", hash_token(flow)[:12])
        return self.public_url + "/signin?flow=" + flow

    async def pending_request(self, flow: str) -> dict | None:
        if not flow or len(flow) > 200:
            return None
        data = await self.state.get_json(self._state_key("authreq", flow))
        return data if isinstance(data, dict) else None

    async def finish_signin(self, flow: str, *, account_id: str) -> str:
        """Call only after the password/CSRF check and encrypted DB commit.

        Consumes pending flow atomically and emits an authorization-code
        redirect to the *already checked* OAuth client's registered URI.
        """
        if not account_id or not await self.store.load(account_id):
            raise TokenError(error="invalid_grant", error_description="Inactive user")
        data = await self.state.take_json(self._state_key("authreq", flow))
        if not isinstance(data, dict):
            raise TokenError(error="invalid_grant", error_description="Login expired")
        code = new_opaque_token()
        data["subject"] = account_id
        data["expires_at"] = time.time() + AUTH_CODE_TTL
        ok = await self.state.put_json(
            self._state_key("code", code), data, ttl=AUTH_CODE_TTL, once=True,
        )
        if not ok:
            raise TokenError(error="invalid_grant", error_description="Login expired")
        return construct_redirect_uri(
            data["redirect_uri"], code=code, state=data.get("state"), iss=self.public_url,
        )

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str,
    ) -> AuthorizationCode | None:
        data = await self.state.get_json(self._state_key("code", authorization_code))
        if (
            not isinstance(data, dict)
            or data.get("client_id") != client.client_id
            or float(data.get("expires_at", 0)) <= time.time()
        ):
            return None
        return AuthorizationCode(
            code=authorization_code, client_id=data["client_id"],
            scopes=data["scopes"], expires_at=data["expires_at"],
            code_challenge=data["code_challenge"], redirect_uri=data["redirect_uri"],
            redirect_uri_provided_explicitly=data["redirect_uri_provided_explicitly"],
            resource=data["resource"], subject=data["subject"],
        )

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode,
    ) -> OAuthToken:
        data = await self.state.take_json(
            self._state_key("code", authorization_code.code),
        )
        if (
            not isinstance(data, dict)
            or data.get("client_id") != client.client_id
            or data.get("subject") != authorization_code.subject
            or data.get("code_challenge") != authorization_code.code_challenge
            or data.get("resource") != self.mcp_url
            or float(data.get("expires_at", 0)) <= time.time()
        ):
            raise TokenError(error="invalid_grant", error_description="Code unavailable")
        return await self._issue(
            user_id=int(data["subject"]), client_id=client.client_id,
            scopes=list(data["scopes"]),
        )

    async def _issue(
        self, *, user_id: int, client_id: str, scopes: list[str],
    ) -> OAuthToken:
        if not await self.store.load(str(user_id)):
            raise TokenError(error="invalid_grant", error_description="Account inactive")
        epoch = await self.store.active_account_epoch(str(user_id))
        if epoch is None:
            raise TokenError(error="invalid_grant", error_description="Inactive company")
        now = int(time.time())
        claims = {
            "iss": self.public_url, "aud": self.mcp_url, "sub": str(user_id),
            "client_id": client_id, "token_use": "access", "jti": new_opaque_token(),
            "iat": now, "nbf": now, "exp": now + ACCESS_TOKEN_TTL,
            "scope": " ".join(scopes),
            "company_epoch": epoch,
        }
        token = jwt.encode(
            claims, self._signing_key, algorithm="HS256", headers={"typ": "at+jwt"},
        )
        refresh = new_opaque_token()
        await self.store.save_refresh(
            refresh, user_id=user_id, client_id=client_id, scopes=scopes,
            resource=self.mcp_url,
            expires_at=datetime.now(UTC) + timedelta(seconds=REFRESH_TOKEN_TTL),
        )
        return OAuthToken(
            access_token=token, token_type="Bearer",
            expires_in=ACCESS_TOKEN_TTL, refresh_token=refresh,
            scope=" ".join(scopes) or None,
        )

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str,
    ) -> RefreshToken | None:
        item = await self.store.get_refresh(refresh_token)
        if (
            not item or item["client_id"] != client.client_id
            or item["resource"] != self.mcp_url
            or item["expires_at"] <= datetime.now(UTC)
        ):
            return None
        return RefreshToken(
            token=refresh_token, client_id=client.client_id,
            scopes=list(item["scopes"]), expires_at=int(item["expires_at"].timestamp()),
            resource=self.mcp_url, subject=str(item["user_id"]),
        )

    async def exchange_refresh_token(
        self, client: OAuthClientInformationFull,
        refresh_token: RefreshToken, scopes: list[str],
    ) -> OAuthToken:
        row = await self.store.take_refresh(refresh_token.token)
        if (
            not row or row["client_id"] != client.client_id
            or row["resource"] != self.mcp_url
            or row["expires_at"] <= datetime.now(UTC)
        ):
            raise TokenError(error="invalid_grant", error_description="Refresh unavailable")
        allowed = list(row["scopes"])
        if not set(scopes).issubset(allowed):
            raise TokenError(error="invalid_scope", error_description="Scope increase denied")
        return await self._issue(
            user_id=int(row["user_id"]), client_id=client.client_id,
            scopes=scopes or allowed,
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        try:
            header = jwt.get_unverified_header(token)
            if header.get("typ") != "at+jwt":
                return None
            claims = jwt.decode(
                token, self._signing_key, algorithms=["HS256"],
                issuer=self.public_url, audience=self.mcp_url,
                options={"require": [
                    "iss", "aud", "sub", "client_id", "token_use", "jti",
                    "iat", "nbf", "exp", "company_epoch",
                ]},
            )
            if (
                claims.get("token_use") != "access"
                or not isinstance(claims.get("sub"), str)
                or not claims["sub"].isascii() or not claims["sub"].isdecimal()
                or not claims.get("client_id") or not claims.get("jti")
                or await self.state.is_revoked(self.public_url, claims["jti"])
                or not isinstance(claims.get("company_epoch"), int)
                or await self.store.active_account_epoch(claims["sub"]) != claims["company_epoch"]
                or not await self.store.load(claims["sub"])
            ):
                return None
        except (InvalidTokenError, ValueError, KeyError, TypeError):
            return None
        except Exception:
            # Storage is unavailable: fail closed, not anonymous fallback.
            return None
        return AccessToken(
            token=token, client_id=claims["client_id"],
            scopes=[x for x in claims.get("scope", "").split() if x],
            expires_at=claims["exp"], resource=self.mcp_url,
            subject=claims["sub"], claims=claims,
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        """Official SDK TokenVerifier protocol."""
        return await self.load_access_token(token)

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        if isinstance(token, RefreshToken):
            await self.store.take_refresh(token.token)
        else:
            claims = token.claims or {}
            jti = claims.get("jti")
            if isinstance(jti, str):
                await self.state.revoke_access_jti(
                    self.public_url, jti,
                    ttl=max(1, int((token.expires_at or time.time()) - time.time())),
                )
            # Revoking a connection must also kill its long-lived refresh path.
            # MVP revokes all refresh sessions of this user, deliberately
            # preferring a conservative policy over orphaned tokens.
            if token.subject and token.subject.isascii() and token.subject.isdecimal():
                await self.store.revoke_user_refresh(int(token.subject))
