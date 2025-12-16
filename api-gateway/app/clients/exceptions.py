"""
Domain-specific exceptions for external API clients.

Maps provider-specific error codes to domain exceptions for better handling
in business logic and consistent error reporting.
"""

from __future__ import annotations


class GeminiClientError(Exception):
    """Base exception for Gemini API client errors."""

    def __init__(
        self, message: str, status_code: int | None = None, retry_after: int | None = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class GeminiRateLimitError(GeminiClientError):
    """
    Raised when Gemini API returns 429 (rate limit exceeded).

    Attributes:
        retry_after: Recommended seconds to wait before retry (from Retry-After header)
    """

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int | None = None):
        super().__init__(message, status_code=429, retry_after=retry_after)


class GeminiServerError(GeminiClientError):
    """
    Raised when Gemini API returns 5xx (server error).

    These errors are typically transient and can be retried.
    """

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message, status_code=status_code)


class GeminiTimeoutError(GeminiClientError):
    """Raised when Gemini API request times out."""

    def __init__(self, message: str = "Request timed out"):
        super().__init__(message)


class GeminiValidationError(GeminiClientError):
    """
    Raised when Gemini API returns invalid or malformed response.

    This can happen when the response doesn't match expected schema
    or contains out-of-range values.
    """

    def __init__(self, message: str):
        super().__init__(message, status_code=422)


class GeminiAuthError(GeminiClientError):
    """Raised when API key is invalid or missing."""

    def __init__(self, message: str = "Invalid or missing API key"):
        super().__init__(message, status_code=401)


class GeminiServiceError(GeminiClientError):
    """
    Raised when Gemini API returns service-level errors (429/503) not related to specific keys.

    These errors indicate temporary service unavailability or overload,
    not key-specific quota/rate limit issues. They should not trigger circuit breaker
    for individual keys and should be retried with fixed delays.
    """

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message, status_code=status_code)


# ============================================================================
# OpenRouter Client Exceptions
# ============================================================================


class OpenRouterClientError(Exception):
    """Base exception for OpenRouter API client errors."""

    def __init__(
        self, message: str, status_code: int | None = None, retry_after: int | None = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class OpenRouterRateLimitError(OpenRouterClientError):
    """Raised when OpenRouter API returns 429 (rate limit exceeded)."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int | None = None):
        super().__init__(message, status_code=429, retry_after=retry_after)


class OpenRouterServerError(OpenRouterClientError):
    """Raised when OpenRouter API returns 5xx (server error)."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message, status_code=status_code)


class OpenRouterTimeoutError(OpenRouterClientError):
    """Raised when OpenRouter API request times out."""

    def __init__(self, message: str = "Request timed out"):
        super().__init__(message)


class OpenRouterValidationError(OpenRouterClientError):
    """Raised when OpenRouter API returns validation error."""

    def __init__(self, message: str):
        super().__init__(message, status_code=422)


class OpenRouterAuthError(OpenRouterClientError):
    """Raised when API key is invalid or missing."""

    def __init__(self, message: str = "Invalid or missing API key"):
        super().__init__(message, status_code=401)


class OpenRouterServiceError(OpenRouterClientError):
    """
    Raised when OpenRouter API returns service-level errors (429/503).

    These errors indicate temporary service unavailability or overload.
    """

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message, status_code=status_code)
