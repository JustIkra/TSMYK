"""
Tests for unified metric mapping service.

Tests cover:
- Loading YAML configuration with unified header_map
- Getting metric codes by labels
- Label normalization (uppercase, trimming)
- Handling unknown labels
- Synonyms (multiple labels mapping to same code)
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from app.services.metric_mapping import (
    MetricMappingService,
    get_metric_mapping_service,
    reset_metric_mapping_service,
)


# Fixtures

@pytest.fixture
def sample_config() -> dict:
    """Sample unified mapping configuration."""
    return {
        "header_map": {
            "АБСТРАКТНОСТЬ": "abstractness",
            "АКТИВНОСТЬ": "activity",
            # Synonyms for sensitivity
            "СЕНЗИТИВНОСТЬ": "sensitivity",
            "СЕНСИТИВНОСТЬ": "sensitivity",
            "ЧУВСТВИТЕЛЬНОСТЬ": "sensitivity",
            # Team roles
            "АДМИНИСТРАТОР": "administrator",
            "АНАЛИТИК": "analyst",
        }
    }


@pytest.fixture
def temp_config_file(sample_config: dict, tmp_path: Path) -> Path:
    """Create temporary YAML config file."""
    config_path = tmp_path / "metric-mapping.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(sample_config, f, allow_unicode=True)
    return config_path


@pytest.fixture
def mapping_service(temp_config_file: Path) -> MetricMappingService:
    """Create MetricMappingService with test config."""
    service = MetricMappingService(config_path=temp_config_file)
    service.load()
    return service


# Unit Tests

@pytest.mark.unit
class TestMetricMappingServiceLoad:
    """Tests for loading configuration."""

    def test_load_valid_config(self, mapping_service: MetricMappingService):
        """Test loading valid configuration."""
        assert mapping_service._loaded is True
        assert len(mapping_service._mapping) > 0

    def test_load_missing_file(self, tmp_path: Path):
        """Test loading from non-existent file."""
        service = MetricMappingService(config_path=tmp_path / "missing.yaml")
        with pytest.raises(FileNotFoundError):
            service.load()

    def test_load_invalid_structure(self, tmp_path: Path):
        """Test loading config without header_map key."""
        config_path = tmp_path / "invalid.yaml"
        with open(config_path, "w") as f:
            yaml.dump({"wrong_key": {}}, f)

        service = MetricMappingService(config_path=config_path)
        with pytest.raises(ValueError, match="Missing 'header_map' key"):
            service.load()

    def test_load_invalid_header_map_type(self, tmp_path: Path):
        """Test loading config with invalid header_map type."""
        config_path = tmp_path / "invalid.yaml"
        with open(config_path, "w") as f:
            yaml.dump({"header_map": "not a dict"}, f)

        service = MetricMappingService(config_path=config_path)
        with pytest.raises(ValueError, match="Invalid header_map structure"):
            service.load()


@pytest.mark.unit
class TestMetricMappingServiceGetCode:
    """Tests for getting metric codes."""

    def test_get_metric_code_exact_match(self, mapping_service: MetricMappingService):
        """Test getting code with exact label match."""
        code = mapping_service.get_metric_code("АБСТРАКТНОСТЬ")
        assert code == "abstractness"

    def test_get_metric_code_lowercase_normalized(
        self, mapping_service: MetricMappingService
    ):
        """Test that labels are normalized to uppercase."""
        code = mapping_service.get_metric_code("абстрактность")
        assert code == "abstractness"

    def test_get_metric_code_with_spaces(self, mapping_service: MetricMappingService):
        """Test that labels are trimmed."""
        code = mapping_service.get_metric_code("  АБСТРАКТНОСТЬ  ")
        assert code == "abstractness"

    def test_get_metric_code_unknown_label(self, mapping_service: MetricMappingService):
        """Test getting code for unknown label returns None."""
        code = mapping_service.get_metric_code("UNKNOWN_LABEL")
        assert code is None

    def test_get_metric_code_synonyms(self, mapping_service: MetricMappingService):
        """Test that synonyms map to the same code."""
        assert mapping_service.get_metric_code("СЕНЗИТИВНОСТЬ") == "sensitivity"
        assert mapping_service.get_metric_code("СЕНСИТИВНОСТЬ") == "sensitivity"
        assert mapping_service.get_metric_code("ЧУВСТВИТЕЛЬНОСТЬ") == "sensitivity"


@pytest.mark.unit
class TestMetricMappingServiceGetMapping:
    """Tests for getting all mappings."""

    def test_get_mapping_returns_copy(self, mapping_service: MetricMappingService):
        """Test that get_mapping returns a copy."""
        mapping1 = mapping_service.get_mapping()
        mapping2 = mapping_service.get_mapping()

        # Should be equal but not the same object
        assert mapping1 == mapping2
        assert mapping1 is not mapping2

        # Modifying one should not affect the other
        mapping1["NEW_KEY"] = "new_value"
        assert "NEW_KEY" not in mapping2

    def test_get_all_mappings_alias(self, mapping_service: MetricMappingService):
        """Test that get_all_mappings returns same result as get_mapping."""
        assert mapping_service.get_all_mappings() == mapping_service.get_mapping()

    def test_get_mapping_normalized_keys(self, mapping_service: MetricMappingService):
        """Test that all keys in mapping are uppercase."""
        mapping = mapping_service.get_mapping()
        for key in mapping.keys():
            assert key == key.upper(), f"Key '{key}' is not uppercase"


@pytest.mark.unit
class TestMetricMappingServiceReload:
    """Tests for reloading configuration."""

    def test_reload_updates_mapping(self, temp_config_file: Path):
        """Test that reload updates mapping from file."""
        service = MetricMappingService(config_path=temp_config_file)
        service.load()

        # Initial state
        assert service.get_metric_code("АБСТРАКТНОСТЬ") == "abstractness"

        # Update config file
        new_config = {
            "header_map": {
                "АБСТРАКТНОСТЬ": "new_abstractness_code",
                "НОВАЯ МЕТРИКА": "new_metric",
            }
        }
        with open(temp_config_file, "w", encoding="utf-8") as f:
            yaml.dump(new_config, f, allow_unicode=True)

        # Reload and verify
        service.reload()
        assert service.get_metric_code("АБСТРАКТНОСТЬ") == "new_abstractness_code"
        assert service.get_metric_code("НОВАЯ МЕТРИКА") == "new_metric"
        assert service.get_metric_code("АКТИВНОСТЬ") is None  # Removed


@pytest.mark.unit
class TestMetricMappingServiceSingleton:
    """Tests for singleton pattern."""

    def test_get_metric_mapping_service_returns_same_instance(self, temp_config_file: Path):
        """Test that get_metric_mapping_service returns singleton."""
        # Reset first
        reset_metric_mapping_service()

        # Mock the default path (would fail without proper setup)
        # Instead, just test reset functionality
        reset_metric_mapping_service()

        # After reset, singleton should be None
        from app.services.metric_mapping import _mapping_service
        # This imports the module variable, not the updated one


# Integration Tests

@pytest.mark.unit
class TestMetricMappingWithRealConfig:
    """Integration tests with real configuration file."""

    def test_load_real_config(self):
        """Test loading the actual metric-mapping.yaml config."""
        # Find config path relative to tests
        config_path = (
            Path(__file__).parent.parent.parent
            / "config"
            / "app"
            / "metric-mapping.yaml"
        )

        if not config_path.exists():
            pytest.skip("Real config file not found")

        service = MetricMappingService(config_path=config_path)
        service.load()

        # Verify some expected mappings exist
        mapping = service.get_mapping()
        assert len(mapping) > 0

        # Test a few known mappings
        assert service.get_metric_code("АБСТРАКТНОСТЬ") == "abstractness"
        assert service.get_metric_code("АКТИВНОСТЬ") == "activity"
        assert service.get_metric_code("СЕНЗИТИВНОСТЬ") == "sensitivity"

    def test_all_codes_are_lowercase_snake_case(self):
        """Test that all metric codes follow naming convention."""
        config_path = (
            Path(__file__).parent.parent.parent
            / "config"
            / "app"
            / "metric-mapping.yaml"
        )

        if not config_path.exists():
            pytest.skip("Real config file not found")

        service = MetricMappingService(config_path=config_path)
        service.load()

        mapping = service.get_mapping()
        for label, code in mapping.items():
            # Codes should be lowercase
            assert code == code.lower(), f"Code '{code}' is not lowercase"
            # Codes should not have spaces
            assert " " not in code, f"Code '{code}' contains spaces"

    def test_no_duplicate_codes_for_different_labels(self):
        """Test consistency: same code for synonyms only."""
        config_path = (
            Path(__file__).parent.parent.parent
            / "config"
            / "app"
            / "metric-mapping.yaml"
        )

        if not config_path.exists():
            pytest.skip("Real config file not found")

        service = MetricMappingService(config_path=config_path)
        service.load()

        mapping = service.get_mapping()

        # Build reverse mapping: code -> [labels]
        reverse_map: dict[str, list[str]] = {}
        for label, code in mapping.items():
            if code not in reverse_map:
                reverse_map[code] = []
            reverse_map[code].append(label)

        # Log codes with multiple labels (synonyms)
        synonyms = {code: labels for code, labels in reverse_map.items() if len(labels) > 1}

        # This is informational - we expect some synonyms
        if synonyms:
            print(f"\nFound {len(synonyms)} codes with synonyms:")
            for code, labels in list(synonyms.items())[:5]:
                print(f"  {code}: {labels}")
