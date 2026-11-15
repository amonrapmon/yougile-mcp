"""Encrypted at-rest YouGile credentials and opaque token hashing.

Adapted from indalo-tech/yougile-mcp-cloud@ea88a0d5, crypto.py.
Copyright (c) Indalo; upstream license AGPL-3.0-only.
SPDX-License-Identifier: AGPL-3.0-only
"""
from __future__ import annotations

import hashlib
import secrets
from collections.abc import Sequence

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from ..config import Secret


class CloudCipher:
    """MultiFernet encryption with key rotation; no plaintext key in DB."""

    def __init__(self, keys: Sequence[str]) -> None:
        if not keys:
            raise ValueError("At least one cloud encryption key is required")
        try:
            self._fernet = MultiFernet([Fernet(key.encode("ascii")) for key in keys])
        except (ValueError, TypeError, UnicodeError) as exc:
            raise ValueError("Invalid cloud encryption key") from exc

    def encrypt(self, secret: Secret) -> bytes:
        if not isinstance(secret, Secret) or not secret.reveal():
            raise ValueError("Nonempty protected YouGile key required")
        return self._fernet.encrypt(secret.reveal().encode("utf-8"))

    def decrypt(self, encrypted: bytes) -> Secret:
        try:
            return Secret(self._fernet.decrypt(bytes(encrypted)).decode("utf-8"))
        except (InvalidToken, UnicodeError, ValueError, TypeError):
            raise ValueError("Unable to decrypt stored YouGile key") from None

    def rotate(self, encrypted: bytes) -> bytes:
        try:
            return self._fernet.rotate(bytes(encrypted))
        except (InvalidToken, ValueError, TypeError):
            raise ValueError("Unable to rotate stored YouGile key") from None


def new_encryption_key() -> str:
    return Fernet.generate_key().decode("ascii")


def new_opaque_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
