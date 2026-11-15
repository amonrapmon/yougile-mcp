"""YouGile sign-in and account provisioning for the Indalo cloud-shell port.

Runs only through the one verified YouGileClient. Passwords are used for
short-lived API authentication and are never stored by this module.
Architectural reference: indalo-tech/yougile-mcp-cloud (AGPL-3.0).
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from ..api import ApiError, YouGileClient
from ..config import Secret, Settings


class CloudSignInError(Exception):
    """Sanitized sign-in failure, safe to show without vendor response details."""


class CloudBadCredentials(CloudSignInError):
    """The submitted YouGile login/password is invalid."""


@dataclass(frozen=True)
class YouGileCompanyChoice:
    id: str
    name: str
    is_admin: bool


@dataclass(frozen=True)
class ProvisionedYouGileAccount:
    company_id: str
    user_id: str
    name: str
    email: str
    is_admin: bool
    api_key: Secret = field(repr=False, compare=False)


class CloudYouGileSignIn:
    """Authenticate a YouGile person and provision a company-bound API key.

    Trusted HTTP endpoints must enforce CSRF, per-login attempt rate limits,
    protected form state and no logging of passwords. This service does not
    implement public routes or OAuth itself.
    """

    def __init__(self, settings: Settings, *, transport: Any = None):
        if settings.company_id is not None or settings.has_api_key:
            raise ValueError("Cloud sign-in cannot use a process-wide YouGile key")
        self.settings = settings
        self.transport = transport

    def _settings_for(self, *, company_id: str | None = None, api_key: str | None = None) -> Settings:
        return replace(
            self.settings,
            company_id=company_id,
            yougile_api_key=Secret(api_key) if api_key else None,
        )

    async def companies(self, login: str, password: str) -> tuple[YouGileCompanyChoice, ...]:
        if not login or not password:
            raise CloudBadCredentials("Invalid YouGile credentials")
        try:
            async with YouGileClient(
                self._settings_for(), transport=self.transport,
            ) as client:
                response = await client.request(
                    "getCompanies",
                    body={"login": login, "password": password},
                    query={"limit": 1000},
                )
        except ApiError as exc:
            if exc.status_code in {400, 401, 403}:
                raise CloudBadCredentials("Invalid YouGile credentials") from None
            raise CloudSignInError("YouGile sign-in temporarily unavailable") from None
        data = response.data
        if not isinstance(data, dict) or not isinstance(data.get("content"), list):
            raise CloudSignInError("Unexpected response from YouGile")
        choices = []
        for company in data["content"]:
            if not isinstance(company, dict) or not isinstance(company.get("id"), str):
                raise CloudSignInError("Unexpected response from YouGile")
            cid = company["id"]
            if not cid:
                raise CloudSignInError("Unexpected response from YouGile")
            choices.append(YouGileCompanyChoice(
                id=cid, name=company.get("name") or cid,
                is_admin=bool(company.get("isAdmin")),
            ))
        return tuple(choices)

    async def _create_key(self, login: str, password: str, company_id: str) -> str:
        try:
            async with YouGileClient(
                self._settings_for(company_id=company_id),
                transport=self.transport,
            ) as client:
                response = await client.request(
                    "AuthKeyController_create",
                    body={"login": login, "password": password, "companyId": company_id},
                )
        except ApiError as exc:
            if exc.status_code in {400, 401, 403}:
                raise CloudBadCredentials("Invalid YouGile credentials or key limit reached") from None
            raise CloudSignInError("Unable to issue a YouGile key") from None
        data = response.data
        if not isinstance(data, dict) or not isinstance(data.get("key"), str) or not data["key"]:
            raise CloudSignInError("Unexpected key response from YouGile")
        return data["key"]

    async def revoke_key(self, key: str) -> None:
        """Revoke one vendor key. Never log or include the key in errors."""
        if not key:
            return
        try:
            async with YouGileClient(
                self._settings_for(), transport=self.transport,
            ) as client:
                await client.request("AuthKeyController_delete", path={"key": key})
        except ApiError as exc:
            # A prior worker can succeed and crash before acknowledging the
            # outbox row. Already-absent keys are therefore successful retries.
            if exc.status_code == 404:
                return
            raise CloudSignInError("Unable to revoke YouGile key") from None

    async def provision(
        self, login: str, password: str, *, selected_company_id: str,
    ) -> ProvisionedYouGileAccount:
        """Validate company choice on the server, issue key, verify ownership.

        The caller persists the returned key only after encryption. If
        verification fails after key issuance we revoke the orphan key.
        """
        choices = await self.companies(login, password)
        if not selected_company_id or selected_company_id not in {x.id for x in choices}:
            raise CloudSignInError("Selected company is not available to this user")
        key = await self._create_key(login, password, selected_company_id)
        try:
            async with YouGileClient(
                self._settings_for(company_id=selected_company_id, api_key=key),
                transport=self.transport,
            ) as client:
                company = await client.request("CompanyController_get")
                if not isinstance(company.data, dict) or company.data.get("id") != selected_company_id:
                    raise CloudSignInError("YouGile company verification failed")
                me = await client.request("UserController_getMe")
                data = me.data
                if not isinstance(data, dict) or not isinstance(data.get("id"), str) or not data["id"]:
                    raise CloudSignInError("Unable to identify YouGile user")
                return ProvisionedYouGileAccount(
                    company_id=selected_company_id,
                    user_id=data["id"],
                    name=data.get("realName") or data.get("email") or "",
                    email=data.get("email") or "",
                    is_admin=bool(data.get("isAdmin")),
                    api_key=Secret(key),
                )
        except BaseException:
            # Best effort on failure, including cancellation. Do not hide the
            # original error or password/token material in an exception.
            try:
                await self.revoke_key(key)
            except CloudSignInError:
                pass
            raise
