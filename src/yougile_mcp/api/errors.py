"""Stable, secret-safe errors raised by the YouGile API core."""

# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SchemaDiagnostic:
    """Sanitized response-schema mismatch metadata; never contains instance values."""

    path: str
    rule: str
    expected_type: str | None
    actual_type: str


class ApiError(Exception):
    """A normalized failure; vendor response bodies are intentionally omitted."""

    category = "upstream_failure"

    def __init__(
        self,
        *,
        status_code: int | None = None,
        retry_after: float | None = None,
        diagnostic: SchemaDiagnostic | None = None,
    ):
        super().__init__(self.category)
        self.status_code = status_code
        self.retry_after = retry_after
        self.diagnostic = diagnostic


class InvalidInputError(ApiError, ValueError):
    category = "invalid_input"


class MissingCredentialsError(ApiError):
    category = "missing_credentials"


class MissingCompanyIdError(ApiError):
    category = "missing_company_id"


class AuthenticationError(ApiError):
    category = "authentication_failed"


class UnsupportedOperationError(ApiError):
    category = "unsupported_operation"


class PermissionDeniedError(ApiError):
    category = "permission_denied"


class NotFoundError(ApiError):
    category = "not_found"


class VendorValidationError(ApiError):
    category = "vendor_validation"


class RateLimitError(ApiError):
    category = "rate_limited"


class RequestBudgetError(ApiError):
    category = "request_budget_exhausted"


class RequestTimeoutError(ApiError):
    category = "timeout"


class UncertainWriteError(ApiError):
    category = "uncertain_write"


class UpstreamError(ApiError):
    category = "upstream_failure"


class PaginationError(ApiError):
    category = "pagination_failure"


class PaginationLimitError(PaginationError):
    category = "pagination_limit"
