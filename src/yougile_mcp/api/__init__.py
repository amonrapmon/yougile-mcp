"""Protocol-neutral YouGile REST API core."""

# SPDX-License-Identifier: AGPL-3.0-only

from .client import CompanyRateLimiter, YouGileClient
from .errors import (
    ApiError,
    AuthenticationError,
    InvalidInputError,
    MissingCompanyIdError,
    MissingCredentialsError,
    NotFoundError,
    PaginationError,
    PaginationLimitError,
    PermissionDeniedError,
    RateLimitError,
    RequestBudgetError,
    RequestTimeoutError,
    UnsupportedOperationError,
    UncertainWriteError,
    UpstreamError,
    VendorValidationError,
)
from .models import ApiResponse

__all__ = [
    "ApiError",
    "ApiResponse",
    "AuthenticationError",
    "CompanyRateLimiter",
    "InvalidInputError",
    "MissingCompanyIdError",
    "MissingCredentialsError",
    "NotFoundError",
    "PaginationError",
    "PaginationLimitError",
    "PermissionDeniedError",
    "RateLimitError",
    "RequestBudgetError",
    "RequestTimeoutError",
    "UnsupportedOperationError",
    "UncertainWriteError",
    "UpstreamError",
    "VendorValidationError",
    "YouGileClient",
]
