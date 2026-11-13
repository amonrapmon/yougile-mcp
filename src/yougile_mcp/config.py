"""Fail-closed environment configuration for future MCP transports.

SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping
from urllib.parse import urlparse


class ConfigError(ValueError):
    """Configuration is invalid or unsafe."""


class Secret:
    """A value that can only be revealed explicitly and prints as redacted."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "Secret(<redacted>)"


@dataclass(frozen=True)
class Settings:
    yougile_base_url: str
    yougile_api_key: Secret | None = field(repr=False, compare=False)
    company_id: str | None = field(repr=False, compare=False)
    transport: str
    host: str
    port: int
    auth_mode: str
    public_url: str | None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        values = os.environ if env is None else env
        base_url = values.get("YOUGILE_BASE_URL", "https://ru.yougile.com").strip()
        parsed_base = urlparse(base_url)
        try:
            parsed_base.port
        except ValueError as exc:
            raise ConfigError("YOUGILE_BASE_URL has an invalid port") from exc
        if (
            parsed_base.scheme != "https"
            or not parsed_base.hostname
            or parsed_base.username
            or parsed_base.password
            or parsed_base.path not in {"", "/"}
            or parsed_base.query
            or parsed_base.fragment
        ):
            raise ConfigError("YOUGILE_BASE_URL must be an HTTPS origin without credentials or path")

        api_key = values.get("YOUGILE_API_KEY", "").strip() or None
        if api_key and any(character in api_key for character in "\r\n"):
            raise ConfigError("YOUGILE_API_KEY contains invalid characters")

        transport = values.get("MCP_TRANSPORT", "stdio").strip().lower()
        if transport not in {"stdio", "http"}:
            raise ConfigError("MCP_TRANSPORT must be stdio or http")

        host = values.get("MCP_HOST", "127.0.0.1").strip()
        if not host:
            raise ConfigError("MCP_HOST cannot be empty")

        raw_port = values.get("MCP_PORT", "8000")
        try:
            port = int(raw_port)
        except ValueError as exc:
            raise ConfigError("MCP_PORT must be an integer") from exc
        if not 1 <= port <= 65535:
            raise ConfigError("MCP_PORT must be between 1 and 65535")

        auth_mode = values.get("MCP_AUTH_MODE", "required").strip().lower()
        if auth_mode != "required":
            raise ConfigError("MCP_AUTH_MODE must be required (no anonymous mode)")

        public_url = values.get("MCP_PUBLIC_URL", "").strip() or None
        if public_url:
            parsed_public = urlparse(public_url)
            if parsed_public.scheme != "https" or not parsed_public.hostname:
                raise ConfigError("MCP_PUBLIC_URL must be an HTTPS URL")

        if transport == "http" and host not in {"localhost", "127.0.0.1", "::1"}:
            if not public_url:
                raise ConfigError("Public HTTP bind requires MCP_PUBLIC_URL with HTTPS")

        return cls(
            yougile_base_url=base_url,
            yougile_api_key=Secret(api_key) if api_key is not None else None,
            company_id=values.get("YOUGILE_COMPANY_ID", "").strip() or None,
            transport=transport,
            host=host,
            port=port,
            auth_mode=auth_mode,
            public_url=public_url,
        )

    @property
    def has_api_key(self) -> bool:
        return self.yougile_api_key is not None

    @property
    def company_id_set(self) -> bool:
        return self.company_id is not None
