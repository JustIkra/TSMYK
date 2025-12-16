"""
Factory for creating AI API clients based on configured provider.

Supports both Gemini and OpenRouter providers with automatic selection
based on AI_PROVIDER setting. Provides dependency injection for FastAPI
routes and Celery tasks.
"""

from __future__ import annotations

import logging
from typing import Union

from app.clients import (
    GeminiClient,
    GeminiPoolClient,
    OpenRouterClient,
    OpenRouterPoolClient,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

# Type alias for any AI client
AIClient = Union[GeminiClient, GeminiPoolClient, OpenRouterClient, OpenRouterPoolClient]


def create_openrouter_client(api_key: str | None = None) -> Union[OpenRouterClient, OpenRouterPoolClient]:
    """
    Create OpenRouter client configured from application settings.

    Args:
        api_key: Optional API key override. If provided, uses single client.

    Returns:
        Configured OpenRouterClient or OpenRouterPoolClient instance
    """
    if not settings.openrouter_keys_list:
        raise ValueError(
            "No OpenRouter API keys configured. "
            "Set OPENROUTER_API_KEYS in .env or switch to Gemini provider."
        )

    # If specific key provided, use single client
    if api_key is not None:
        client = OpenRouterClient(
            api_key=api_key,
            model_text=settings.openrouter_model_text,
            model_vision=settings.openrouter_model_vision,
            timeout_s=settings.openrouter_timeout_s,
            max_retries=3,
            base_url=settings.openrouter_base_url,
            app_url=settings.openrouter_app_url,
            app_name=settings.openrouter_app_name,
        )

        logger.debug(
            "openrouter_single_client_created",
            extra={
                "model_text": settings.openrouter_model_text,
                "model_vision": settings.openrouter_model_vision,
            },
        )

        return client

    # Multiple keys: use pool client
    if len(settings.openrouter_keys_list) > 1:
        client = OpenRouterPoolClient(
            api_keys=settings.openrouter_keys_list,
            model_text=settings.openrouter_model_text,
            model_vision=settings.openrouter_model_vision,
            timeout_s=settings.openrouter_timeout_s,
            max_retries=3,
            base_url=settings.openrouter_base_url,
            app_url=settings.openrouter_app_url,
            app_name=settings.openrouter_app_name,
            qps_per_key=settings.openrouter_qps_per_key,
            burst_multiplier=settings.openrouter_burst_multiplier,
            strategy=settings.openrouter_strategy,
        )

        logger.info(
            "openrouter_pool_client_created",
            extra={
                "total_keys": len(settings.openrouter_keys_list),
                "qps_per_key": settings.openrouter_qps_per_key,
                "strategy": settings.openrouter_strategy,
                "model_text": settings.openrouter_model_text,
            },
        )

        return client

    # Single key: use simple client
    client = OpenRouterClient(
        api_key=settings.openrouter_keys_list[0],
        model_text=settings.openrouter_model_text,
        model_vision=settings.openrouter_model_vision,
        timeout_s=settings.openrouter_timeout_s,
        max_retries=3,
        base_url=settings.openrouter_base_url,
        app_url=settings.openrouter_app_url,
        app_name=settings.openrouter_app_name,
    )

    logger.debug(
        "openrouter_single_client_created",
        extra={
            "model_text": settings.openrouter_model_text,
            "model_vision": settings.openrouter_model_vision,
        },
    )

    return client


def create_gemini_client(api_key: str | None = None) -> Union[GeminiClient, GeminiPoolClient]:
    """
    Create Gemini client configured from application settings.

    Args:
        api_key: Optional API key override. If provided, uses single client.

    Returns:
        Configured GeminiClient or GeminiPoolClient instance
    """
    if not settings.gemini_keys_list:
        raise ValueError(
            "No Gemini API keys configured. "
            "Set GEMINI_API_KEYS in .env or switch to OpenRouter provider."
        )

    # If specific key provided, use single client
    if api_key is not None:
        client = GeminiClient(
            api_key=api_key,
            model_text=settings.gemini_model_text,
            model_vision=settings.gemini_model_vision,
            timeout_s=settings.gemini_timeout_s,
            max_retries=3,
        )

        logger.debug(
            "gemini_single_client_created",
            extra={
                "model_text": settings.gemini_model_text,
                "model_vision": settings.gemini_model_vision,
            },
        )

        return client

    # Multiple keys: use pool client
    if len(settings.gemini_keys_list) > 1:
        client = GeminiPoolClient(
            api_keys=settings.gemini_keys_list,
            model_text=settings.gemini_model_text,
            model_vision=settings.gemini_model_vision,
            timeout_s=settings.gemini_timeout_s,
            max_retries=3,
            qps_per_key=settings.gemini_qps_per_key,
            burst_multiplier=settings.gemini_burst_multiplier,
            strategy=settings.gemini_strategy,
        )

        logger.info(
            "gemini_pool_client_created",
            extra={
                "total_keys": len(settings.gemini_keys_list),
                "qps_per_key": settings.gemini_qps_per_key,
                "strategy": settings.gemini_strategy,
            },
        )

        return client

    # Single key: use simple client
    client = GeminiClient(
        api_key=settings.gemini_keys_list[0],
        model_text=settings.gemini_model_text,
        model_vision=settings.gemini_model_vision,
        timeout_s=settings.gemini_timeout_s,
        max_retries=3,
    )

    logger.debug(
        "gemini_single_client_created",
        extra={
            "model_text": settings.gemini_model_text,
            "model_vision": settings.gemini_model_vision,
        },
    )

    return client


def create_ai_client(api_key: str | None = None) -> AIClient:
    """
    Create AI client based on configured provider (AI_PROVIDER setting).

    This is the main factory function that should be used throughout
    the application for AI operations.

    Args:
        api_key: Optional API key override.

    Returns:
        Configured AI client (Gemini or OpenRouter based on settings)
    """
    if settings.ai_provider == "openrouter":
        return create_openrouter_client(api_key)
    else:
        return create_gemini_client(api_key)


async def get_ai_client() -> AIClient:
    """
    FastAPI dependency for injecting AI client.

    Returns client based on AI_PROVIDER setting.

    Example:
        ```python
        @router.post("/analyze")
        async def analyze(client = Depends(get_ai_client)):
            response = await client.generate_text("Analyze this...")
            return response
        ```

    Returns:
        Configured AI client instance
    """
    return create_ai_client()


def extract_text_from_response(response: dict) -> str:
    """
    Extract text content from AI response (handles both Gemini and OpenRouter formats).

    Args:
        response: Raw API response

    Returns:
        Extracted text content
    """
    # OpenRouter format: choices[0].message.content
    if "choices" in response:
        return response["choices"][0]["message"]["content"]

    # Gemini format: candidates[0].content.parts[0].text
    if "candidates" in response:
        return response["candidates"][0]["content"]["parts"][0]["text"]

    raise ValueError(f"Unknown response format: {list(response.keys())}")
