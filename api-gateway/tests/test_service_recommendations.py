"""
Unit tests for recommendations generator service.

Tests cover:
- _build_prompt: Structured prompt generation
- _truncate_response: List truncation to max 5 items
- _extract_text_from_response: Response parsing
- _build_self_heal_prompt: Retry prompt generation
- Error handling for invalid JSON

Markers:
- unit: Pure unit tests with mocked Gemini client
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.clients.exceptions import GeminiClientError
from app.schemas.recommendations import RecommendationsInput
from app.services.recommendations import RecommendationsGenerator


@pytest.mark.unit
class TestBuildPrompt:
    """Test the _build_prompt method."""

    def test_build_prompt_includes_activity_name(self):
        """
        Test that prompt includes professional activity name.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        input_data = RecommendationsInput(
            context={
                "language": "ru",
                "prof_activity": {
                    "code": "developer",
                    "name": "Разработчик ПО",
                },
            },
            metrics=[
                {
                    "code": "metric_1",
                    "name": "Метрика 1",
                    "value": "8.0",
                    "weight": "0.5",
                }
            ],
            score_pct=80.0,
        )

        # Act
        prompt = generator._build_prompt(input_data)

        # Assert
        assert "Разработчик ПО" in prompt
        assert "Верни только JSON по схеме" in prompt

    def test_build_prompt_includes_metrics(self):
        """
        Test that prompt includes all metrics data.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        input_data = RecommendationsInput(
            context={
                "language": "ru",
                "prof_activity": {"code": "test", "name": "Test Activity"},
            },
            metrics=[
                {
                    "code": "metric_a",
                    "name": "Метрика А",
                    "value": "7.5",
                    "weight": "0.6",
                },
                {
                    "code": "metric_b",
                    "name": "Метрика Б",
                    "value": "5.0",
                    "weight": "0.4",
                },
            ],
            score_pct=65.0,
        )

        # Act
        prompt = generator._build_prompt(input_data)

        # Assert
        assert "metric_a" in prompt
        assert "metric_b" in prompt
        assert "7.5" in prompt
        assert "5.0" in prompt

    def test_build_prompt_includes_score_pct(self):
        """
        Test that prompt includes score_pct.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        input_data = RecommendationsInput(
            context={
                "language": "ru",
                "prof_activity": {"code": "test", "name": "Test"},
            },
            metrics=[],
            score_pct=75.5,
        )

        # Act
        prompt = generator._build_prompt(input_data)

        # Assert
        assert "75.5" in prompt

    def test_build_prompt_includes_requirements(self):
        """
        Test that prompt includes all requirements.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        input_data = RecommendationsInput(
            context={
                "language": "ru",
                "prof_activity": {"code": "test", "name": "Test"},
            },
            metrics=[],
            score_pct=50.0,
        )

        # Act
        prompt = generator._build_prompt(input_data)

        # Assert
        assert "максимум 5 элементов" in prompt
        assert "title: максимум 80 символов" in prompt
        assert "НЕ используй URL" in prompt


@pytest.mark.unit
class TestTruncateResponse:
    """Test the _truncate_response method."""

    def test_truncate_strengths_to_5_items(self):
        """
        Test that strengths list is truncated to max 5 items.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        data = {
            "strengths": [
                {"title": f"Strength {i}", "metric_codes": [f"code{i}"], "reason": f"Reason {i}"}
                for i in range(10)  # 10 items
            ],
            "dev_areas": [],
            "recommendations": [],
        }

        # Act
        result = generator._truncate_response(data)

        # Assert
        assert len(result["strengths"]) == 5

    def test_truncate_dev_areas_to_5_items(self):
        """
        Test that dev_areas list is truncated to max 5 items.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        data = {
            "strengths": [],
            "dev_areas": [
                {"title": f"Area {i}", "metric_codes": [f"code{i}"], "actions": [f"Action {i}"]}
                for i in range(8)  # 8 items
            ],
            "recommendations": [],
        }

        # Act
        result = generator._truncate_response(data)

        # Assert
        assert len(result["dev_areas"]) == 5

    def test_truncate_recommendations_to_5_items(self):
        """
        Test that recommendations list is truncated to max 5 items.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        data = {
            "strengths": [],
            "dev_areas": [],
            "recommendations": [
                {
                    "title": f"Rec {i}",
                    "skill_focus": f"Skill {i}",
                    "development_advice": f"Advice {i}",
                    "recommended_formats": [f"Format {i}"],
                }
                for i in range(7)  # 7 items
            ],
        }

        # Act
        result = generator._truncate_response(data)

        # Assert
        assert len(result["recommendations"]) == 5

    def test_truncate_title_to_80_chars(self):
        """
        Test that title field is truncated to 80 characters.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        long_title = "A" * 150  # 150 characters

        data = {
            "strengths": [
                {"title": long_title, "metric_codes": ["code1"], "reason": "Reason"}
            ],
            "dev_areas": [],
            "recommendations": [],
        }

        # Act
        result = generator._truncate_response(data)

        # Assert
        assert len(result["strengths"][0]["title"]) == 80

    def test_truncate_reason_to_200_chars(self):
        """
        Test that reason field is truncated to 200 characters.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        long_reason = "B" * 300  # 300 characters

        data = {
            "strengths": [
                {"title": "Title", "metric_codes": ["code1"], "reason": long_reason}
            ],
            "dev_areas": [],
            "recommendations": [],
        }

        # Act
        result = generator._truncate_response(data)

        # Assert
        assert len(result["strengths"][0]["reason"]) == 200

    def test_truncate_skill_focus_to_120_chars(self):
        """
        Test that skill_focus field is truncated to 120 characters.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        long_skill = "C" * 200  # 200 characters

        data = {
            "strengths": [],
            "dev_areas": [],
            "recommendations": [
                {
                    "title": "Title",
                    "skill_focus": long_skill,
                    "development_advice": "Advice",
                    "recommended_formats": [],
                }
            ],
        }

        # Act
        result = generator._truncate_response(data)

        # Assert
        assert len(result["recommendations"][0]["skill_focus"]) == 120

    def test_truncate_development_advice_to_240_chars(self):
        """
        Test that development_advice field is truncated to 240 characters.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        long_advice = "D" * 400  # 400 characters

        data = {
            "strengths": [],
            "dev_areas": [],
            "recommendations": [
                {
                    "title": "Title",
                    "skill_focus": "Skill",
                    "development_advice": long_advice,
                    "recommended_formats": [],
                }
            ],
        }

        # Act
        result = generator._truncate_response(data)

        # Assert
        assert len(result["recommendations"][0]["development_advice"]) == 240

    def test_truncate_actions_to_5_items(self):
        """
        Test that actions list in dev_areas is truncated to 5 items.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        data = {
            "strengths": [],
            "dev_areas": [
                {
                    "title": "Area",
                    "metric_codes": ["code1"],
                    "actions": [f"Action {i}" for i in range(10)],  # 10 actions
                }
            ],
            "recommendations": [],
        }

        # Act
        result = generator._truncate_response(data)

        # Assert
        assert len(result["dev_areas"][0]["actions"]) == 5

    def test_truncate_recommended_formats_to_5_items(self):
        """
        Test that recommended_formats list is truncated to 5 items.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        data = {
            "strengths": [],
            "dev_areas": [],
            "recommendations": [
                {
                    "title": "Rec",
                    "skill_focus": "Skill",
                    "development_advice": "Advice",
                    "recommended_formats": [f"Format {i}" for i in range(10)],  # 10 formats
                }
            ],
        }

        # Act
        result = generator._truncate_response(data)

        # Assert
        assert len(result["recommendations"][0]["recommended_formats"]) == 5

    def test_truncate_preserves_structure(self):
        """
        Test that truncation preserves the original data structure.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        data = {
            "strengths": [
                {"title": "S1", "metric_codes": ["c1"], "reason": "R1"}
            ],
            "dev_areas": [
                {"title": "D1", "metric_codes": ["c2"], "actions": ["A1"]}
            ],
            "recommendations": [
                {
                    "title": "Rec1",
                    "skill_focus": "Skill1",
                    "development_advice": "Advice1",
                    "recommended_formats": ["F1"],
                }
            ],
        }

        # Act
        result = generator._truncate_response(data)

        # Assert
        assert "strengths" in result
        assert "dev_areas" in result
        assert "recommendations" in result
        assert result["strengths"][0]["metric_codes"] == ["c1"]


@pytest.mark.unit
class TestExtractTextFromResponse:
    """Test the _extract_text_from_response method."""

    def test_extract_text_valid_response(self):
        """
        Test successful text extraction from valid Gemini response.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Valid response text"}
                        ]
                    }
                }
            ]
        }

        # Act
        result = generator._extract_text_from_response(response)

        # Assert
        assert result == "Valid response text"

    def test_extract_text_no_candidates_raises_error(self):
        """
        Test that ValueError is raised when no candidates in response.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        response = {
            "candidates": []
        }

        # Act & Assert
        with pytest.raises(ValueError, match="No candidates in response"):
            generator._extract_text_from_response(response)

    def test_extract_text_no_parts_raises_error(self):
        """
        Test that ValueError is raised when no parts in content.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        response = {
            "candidates": [
                {
                    "content": {
                        "parts": []
                    }
                }
            ]
        }

        # Act & Assert
        with pytest.raises(ValueError, match="No parts in content"):
            generator._extract_text_from_response(response)

    def test_extract_text_empty_text_raises_error(self):
        """
        Test that ValueError is raised when text is empty.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        response = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": ""}
                        ]
                    }
                }
            ]
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Empty text in response"):
            generator._extract_text_from_response(response)

    def test_extract_text_malformed_response_raises_error(self):
        """
        Test that ValueError is raised for malformed response structure.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        response = {
            "invalid_key": "invalid_value"
        }

        # Act & Assert
        # The implementation raises "No candidates in response" for this case
        with pytest.raises(ValueError, match="No candidates in response"):
            generator._extract_text_from_response(response)


@pytest.mark.unit
class TestBuildSelfHealPrompt:
    """Test the _build_self_heal_prompt method."""

    def test_self_heal_prompt_includes_invalid_json(self):
        """
        Test that self-heal prompt includes the invalid JSON.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        invalid_json = '{"invalid": "json'

        # Act
        prompt = generator._build_self_heal_prompt(invalid_json)

        # Assert
        assert "Невалидный ответ:" in prompt
        assert invalid_json in prompt

    def test_self_heal_prompt_includes_schema(self):
        """
        Test that self-heal prompt includes the required schema.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        # Act
        prompt = generator._build_self_heal_prompt("invalid")

        # Assert
        assert "strengths" in prompt
        assert "dev_areas" in prompt
        assert "recommendations" in prompt

    def test_self_heal_prompt_includes_requirements(self):
        """
        Test that self-heal prompt includes requirements.
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        # Act
        prompt = generator._build_self_heal_prompt("invalid")

        # Assert
        assert "максимум 5 элементов" in prompt
        assert "НЕ используй URL" in prompt

    def test_self_heal_prompt_includes_long_invalid_json(self):
        """
        Test that self-heal prompt includes invalid JSON (implementation doesn't truncate).
        """
        # Arrange
        mock_client = MagicMock()
        generator = RecommendationsGenerator(gemini_client=mock_client)

        long_invalid_json = "A" * 1000  # 1000 characters

        # Act
        prompt = generator._build_self_heal_prompt(long_invalid_json)

        # Assert - Implementation includes first 500 chars in the prompt
        # (The [:500] is in the implementation at line 437)
        assert long_invalid_json[:500] in prompt


@pytest.mark.unit
class TestSystemInstructions:
    """Test system instructions constant."""

    def test_system_instructions_exist(self):
        """
        Test that SYSTEM_INSTRUCTIONS constant exists and is not empty.
        """
        # Act
        instructions = RecommendationsGenerator.SYSTEM_INSTRUCTIONS

        # Assert
        assert instructions is not None
        assert len(instructions) > 0

    def test_system_instructions_include_key_rules(self):
        """
        Test that system instructions include key rules.
        """
        # Act
        instructions = RecommendationsGenerator.SYSTEM_INSTRUCTIONS

        # Assert
        assert "эксперт" in instructions
        assert "JSON" in instructions
        assert "по-русски" in instructions


@pytest.mark.unit
class TestJSONSchema:
    """Test JSON schema constant."""

    def test_json_schema_has_required_fields(self):
        """
        Test that JSON_SCHEMA has all required top-level fields.
        """
        # Act
        schema = RecommendationsGenerator.JSON_SCHEMA

        # Assert
        assert "type" in schema
        assert schema["type"] == "object"
        assert "required" in schema
        assert set(schema["required"]) == {"strengths", "dev_areas", "recommendations"}

    def test_json_schema_strengths_max_items(self):
        """
        Test that strengths has maxItems constraint.
        """
        # Act
        schema = RecommendationsGenerator.JSON_SCHEMA

        # Assert
        assert schema["properties"]["strengths"]["maxItems"] == 5

    def test_json_schema_dev_areas_max_items(self):
        """
        Test that dev_areas has maxItems constraint.
        """
        # Act
        schema = RecommendationsGenerator.JSON_SCHEMA

        # Assert
        assert schema["properties"]["dev_areas"]["maxItems"] == 5

    def test_json_schema_recommendations_max_items(self):
        """
        Test that recommendations has maxItems constraint.
        """
        # Act
        schema = RecommendationsGenerator.JSON_SCHEMA

        # Assert
        assert schema["properties"]["recommendations"]["maxItems"] == 5
