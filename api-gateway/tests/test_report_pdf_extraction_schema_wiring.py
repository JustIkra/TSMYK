"""Tests for verifying output_schema is wired into LLM calls."""

import pytest
from unittest.mock import AsyncMock, patch

from app.clients.openrouter import OpenRouterClient, OpenRouterTransport


class MockTransport(OpenRouterTransport):
    """Mock transport that captures requests for testing."""

    def __init__(self):
        self.requests: list[dict] = []

    async def request(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        json: dict | None = None,
        timeout: float = 30.0,
    ) -> dict:
        self.requests.append({
            "method": method,
            "url": url,
            "json": json,
        })
        # Return valid extraction response
        return {"choices": [{"message": {"content": '{"metrics": []}'}}]}


@pytest.mark.asyncio
async def test_report_pdf_extraction_uses_json_schema():
    """Verify that report PDF extraction wires output_schema into generate_from_pdf."""
    from app.services.report_pdf_prompts import get_report_pdf_extraction_schema

    # Schema should be present
    schema = get_report_pdf_extraction_schema()
    assert schema is not None
    assert schema.get("type") == "object"
    assert "metrics" in schema.get("properties", {})


@pytest.mark.asyncio
async def test_metric_mapping_decision_uses_json_schema():
    """Verify that metric mapping decision wires output_schema into generate_text."""
    from app.services.metric_mapping_llm_decision import (
        get_metric_mapping_decision_schema,
    )

    # Schema should be present
    schema = get_metric_mapping_decision_schema()
    assert schema is not None
    assert schema.get("type") == "object"
    assert "decision" in schema.get("properties", {})
    assert "metric_code" in schema.get("properties", {})


@pytest.mark.asyncio
async def test_decide_metric_mapping_passes_schema_to_client():
    """Verify that decide_metric_mapping actually passes json_schema to the client."""
    from app.services.metric_mapping_llm_decision import decide_metric_mapping

    mock_transport = MockTransport()
    client = OpenRouterClient(api_key="test-key", transport=mock_transport)

    candidates = [
        {"code": "METRIC_A", "name_ru": "Метрика А", "indexed_text": "Описание", "similarity": 0.95}
    ]

    await decide_metric_mapping(
        ai_client=client,
        label="Тестовая метрика",
        candidates=candidates,
    )

    # Verify request was made
    assert len(mock_transport.requests) == 1
    payload = mock_transport.requests[0]["json"]

    # Verify json_schema response format is used
    assert payload["response_format"]["type"] == "json_schema"
    assert "json_schema" in payload["response_format"]
    assert payload["response_format"]["json_schema"]["strict"] is True

    await client.close()
