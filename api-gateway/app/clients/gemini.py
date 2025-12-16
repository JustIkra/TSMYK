"""
Gemini API client with retry logic, timeout handling, and error mapping.

Supports both text generation and vision tasks with configurable timeouts
and exponential backoff for transient errors (429, 5xx).
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.clients.exceptions import (
    GeminiAuthError,
    GeminiClientError,
    GeminiRateLimitError,
    GeminiServerError,
    GeminiServiceError,
    GeminiTimeoutError,
    GeminiValidationError,
)

logger = logging.getLogger(__name__)


class GeminiTransport(ABC):
    """
    Abstract transport layer for Gemini API calls.

    This interface allows mocking HTTP requests in tests without
    requiring actual network calls or complex patching.
    """

    @abstractmethod
    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """
        Execute HTTP request and return parsed JSON response.

        Args:
            method: HTTP method (GET, POST)
            url: Full request URL
            headers: Request headers
            json: Request body (for POST)
            timeout: Request timeout in seconds

        Returns:
            Parsed JSON response

        Raises:
            GeminiClientError: On any error (rate limit, timeout, server error)
        """
        pass


class HttpxTransport(GeminiTransport):
    """
    Production transport using httpx for actual HTTP requests.

    Handles connection pooling, retries, and proper resource cleanup.
    """

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create httpx client (lazy initialization)."""
        if self._client is None:
            # Import settings to check VPN configuration
            from app.core.config import settings

            # Configure SOCKS5 proxy if Hysteria2 VPN is enabled
            proxy_url = None
            if settings.vpn_enabled and settings.vpn_type == "hysteria2":
                proxy_url = f"socks5://127.0.0.1:{settings.hysteria2_socks5_port}"
                logger.info(
                    "gemini_client_using_socks5_proxy",
                    extra={
                        "proxy": proxy_url,
                        "vpn_type": settings.vpn_type,
                    },
                )

            self._client = httpx.AsyncClient(
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
                follow_redirects=True,
                proxy=proxy_url,
            )
        return self._client

    async def close(self) -> None:
        """Close httpx client and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Execute HTTP request using httpx."""
        client = await self._get_client()

        try:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=json,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException as e:
            logger.warning("gemini_timeout", extra={"url": url, "timeout": timeout})
            raise GeminiTimeoutError(f"Request timed out after {timeout}s") from e

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            response_text_raw = e.response.text
            response_snippet = response_text_raw[:500] if response_text_raw else ""

            # Extract retry-after header if present
            retry_after = None
            if "retry-after" in e.response.headers:
                try:
                    retry_after = int(e.response.headers["retry-after"])
                except ValueError:
                    pass

            # Map HTTP errors to domain exceptions
            if status_code == 429:
                # Distinguish between key-specific rate limits and service-level overload
                # Check response body for indicators of key-specific issues
                response_text = response_text_raw.lower()
                is_key_specific = (
                    "quota" in response_text
                    or "api key" in response_text
                    or "rate limit" in response_text
                    or "per key" in response_text
                )

                if is_key_specific:
                    # Key-specific rate limit (quota exceeded for this key)
                    logger.warning(
                        "gemini_rate_limit_key",
                        extra={
                            "url": url,
                            "retry_after": retry_after,
                            "response": response_snippet,
                        },
                    )
                    raise GeminiRateLimitError(retry_after=retry_after) from e
                else:
                    # Service-level overload (429 from service, not key quota)
                    logger.warning(
                        "gemini_service_overload",
                        extra={
                            "url": url,
                            "retry_after": retry_after,
                            "response": response_snippet,
                        },
                    )
                    raise GeminiServiceError(
                        f"Service overload (429): {e.response.text[:200]}", status_code=429
                    ) from e

            elif status_code == 503:
                # Service unavailable - always a service error, not key-specific
                logger.warning(
                    "gemini_service_unavailable",
                    extra={"url": url, "response": response_snippet},
                )
                raise GeminiServiceError(
                    f"Service unavailable (503): {e.response.text[:200]}", status_code=503
                ) from e

            elif status_code == 401 or status_code == 403:
                logger.error("gemini_auth_error", extra={"url": url, "status": status_code})
                raise GeminiAuthError("Invalid or missing API key") from e

            elif 400 <= status_code < 500:
                logger.warning(
                    "gemini_client_error",
                    extra={"url": url, "status": status_code, "response": e.response.text[:500]},
                )
                raise GeminiValidationError(
                    f"Client error {status_code}: {e.response.text[:200]}"
                ) from e

            elif status_code >= 500:
                # Other 5xx errors (besides 503) are also service errors
                logger.warning(
                    "gemini_server_error",
                    extra={"url": url, "status": status_code, "response": response_snippet},
                )
                raise GeminiServerError(
                    f"Server error {status_code}", status_code=status_code
                ) from e

            else:
                # Unexpected status code
                raise GeminiClientError(
                    f"Unexpected status {status_code}", status_code=status_code
                ) from e

        except httpx.RequestError as e:
            logger.error("gemini_network_error", extra={"url": url, "error": str(e)})
            raise GeminiClientError(f"Network error: {e}") from e




class GeminiClient:
    """
    Gemini API client with retry logic and error handling.

    Features:
    - Exponential backoff for 429/5xx errors
    - Configurable timeouts per request
    - Domain-specific exceptions
    - Mockable transport layer

    Example:
        ```python
        client = GeminiClient(
            api_key="your-key",
            model_text="gemini-2.5-flash",
            timeout_s=30,
        )

        response = await client.generate_text(
            prompt="Explain quantum computing",
            system_instructions="You are a physics teacher.",
        )
        ```
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: str,
        model_text: str = "gemini-2.5-flash",
        model_vision: str = "gemini-2.5-flash",
        timeout_s: int = 30,
        max_retries: int = 3,
        transport: GeminiTransport | None = None,
    ):
        """
        Initialize Gemini client.

        Args:
            api_key: Gemini API key
            model_text: Model name for text generation
            model_vision: Model name for vision tasks
            timeout_s: Default request timeout in seconds
            max_retries: Maximum retry attempts for transient errors
            transport: Custom transport (for testing); if None, uses HttpxTransport
        """
        self.api_key = api_key
        self.model_text = model_text
        self.model_vision = model_vision
        self.timeout_s = timeout_s
        self.max_retries = max_retries

        # Initialize transport
        if transport is not None:
            self.transport = transport
        else:
            self.transport = HttpxTransport()

    async def close(self) -> None:
        """Close client and release resources."""
        if hasattr(self.transport, "close"):
            await self.transport.close()

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        Execute request with exponential backoff for transient errors.

        Retries on:
        - 429 (rate limit)
        - 5xx (server errors)
        - Timeout errors
        - Service errors (429/503 from service, not key-specific)

        Does NOT retry on:
        - 4xx (client errors like validation, auth)
        """
        timeout = timeout or self.timeout_s
        last_exception: Exception | None = None

        # Execute at least once, even if max_retries=0
        attempts = max(1, self.max_retries)

        for attempt in range(attempts):
            try:
                return await self.transport.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json,
                    timeout=timeout,
                )

            except GeminiServiceError as e:
                # Service errors (429/503 from service) use fixed 30-second timeout
                last_exception = e
                is_last_attempt = attempt == attempts - 1

                if is_last_attempt:
                    logger.warning(
                        "gemini_max_retries_exceeded",
                        extra={
                            "url": url,
                            "attempts": attempt + 1,
                            "error": str(e),
                            "error_type": "GeminiServiceError",
                        },
                    )
                    raise

                # Fixed 30-second timeout for service errors (no exponential backoff)
                delay = 30

                logger.info(
                    "gemini_service_error_retry",
                    extra={
                        "url": url,
                        "attempt": attempt + 1,
                        "delay": delay,
                        "status_code": e.status_code,
                    },
                )

                await asyncio.sleep(delay)

            except (GeminiRateLimitError, GeminiServerError, GeminiTimeoutError) as e:
                last_exception = e
                is_last_attempt = attempt == attempts - 1

                if is_last_attempt:
                    logger.warning(
                        "gemini_max_retries_exceeded",
                        extra={
                            "url": url,
                            "attempts": attempt + 1,
                            "error": str(e),
                        },
                    )
                    raise

                # Calculate backoff delay
                if isinstance(e, GeminiRateLimitError) and e.retry_after:
                    # Use server-provided retry-after if available
                    delay = e.retry_after
                else:
                    # Exponential backoff: 1s, 2s, 4s
                    delay = 2**attempt

                logger.info(
                    "gemini_retry_scheduled",
                    extra={
                        "url": url,
                        "attempt": attempt + 1,
                        "delay": delay,
                        "error_type": type(e).__name__,
                    },
                )

                await asyncio.sleep(delay)

            except GeminiClientError:
                # Non-retryable errors (auth, validation)
                raise

        # Should never reach here, but for type safety
        if last_exception:
            raise last_exception
        raise GeminiClientError("Retry loop ended unexpectedly")

    async def generate_text(
        self,
        prompt: str,
        system_instructions: str | None = None,
        response_mime_type: str = "text/plain",
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        Generate text using Gemini text model.

        Args:
            prompt: User prompt
            system_instructions: System instructions (optional)
            response_mime_type: Response MIME type (text/plain or application/json)
            timeout: Request timeout (uses default if None)

        Returns:
            Gemini API response with generated text

        Raises:
            GeminiClientError: On API errors, rate limits, or timeouts
        """
        url = f"{self.BASE_URL}/models/{self.model_text}:generateContent"

        # Build request payload
        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}], "role": "user"}],
            "generationConfig": {"responseMimeType": response_mime_type},
        }

        if system_instructions:
            payload["systemInstruction"] = {"parts": [{"text": system_instructions}]}

        headers = {"Content-Type": "application/json"}

        logger.debug(
            "gemini_text_request",
            extra={
                "model": self.model_text,
                "prompt_length": len(prompt),
                "has_system": system_instructions is not None,
            },
        )

        return await self._request_with_retry(
            method="POST",
            url=f"{url}?key={self.api_key}",
            headers=headers,
            json=payload,
            timeout=timeout,
        )

    async def generate_from_image(
        self,
        prompt: str,
        image_data: bytes,
        mime_type: str = "image/png",
        response_mime_type: str = "application/json",
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """
        Generate content from image using Gemini vision model.

        Args:
            prompt: User prompt describing what to extract
            image_data: Image bytes
            mime_type: Image MIME type (image/png, image/jpeg)
            response_mime_type: Response MIME type (typically application/json)
            timeout: Request timeout (uses default if None)

        Returns:
            Gemini API response with extracted data

        Raises:
            GeminiClientError: On API errors, rate limits, or timeouts
        """
        import base64

        url = f"{self.BASE_URL}/models/{self.model_vision}:generateContent"

        # Encode image to base64
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        # Build request payload
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {"inlineData": {"mimeType": mime_type, "data": image_b64}},
                    ],
                    "role": "user",
                }
            ],
            "generationConfig": {"responseMimeType": response_mime_type},
        }

        headers = {"Content-Type": "application/json"}

        logger.debug(
            "gemini_vision_request",
            extra={
                "model": self.model_vision,
                "prompt_length": len(prompt),
                "image_size": len(image_data),
                "mime_type": mime_type,
            },
        )

        return await self._request_with_retry(
            method="POST",
            url=f"{url}?key={self.api_key}",
            headers=headers,
            json=payload,
            timeout=timeout,
        )

    def __repr__(self) -> str:
        return (
            f"GeminiClient(model_text={self.model_text}, "
            f"model_vision={self.model_vision}, "
            f"timeout={self.timeout_s}s)"
        )
