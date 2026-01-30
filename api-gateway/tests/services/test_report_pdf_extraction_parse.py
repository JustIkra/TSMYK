"""Tests for PDF extraction parsing functions."""

import pytest


@pytest.mark.unit
def test_parse_pdf_metrics_accepts_numbers_and_strings():
    """Metric values can be numbers or strings, both should parse correctly."""
    from app.services.report_pdf_extraction import _parse_pdf_metrics

    parsed = _parse_pdf_metrics(
        {"metrics": [{"label": "Leadership", "value": "7.5"}, {"label": "Teamwork", "value": 8}]}
    )
    assert len(parsed) == 2
    assert parsed[0]["label"] == "Leadership"
    assert parsed[0]["value"] == "7.5"
    assert parsed[1]["label"] == "Teamwork"
    assert parsed[1]["value"] == "8"


@pytest.mark.unit
def test_parse_pdf_metrics_strips_whitespace():
    """Labels and values should have whitespace trimmed."""
    from app.services.report_pdf_extraction import _parse_pdf_metrics

    parsed = _parse_pdf_metrics(
        {"metrics": [{"label": "  Test Label  ", "value": " 5.5 "}]}
    )
    assert len(parsed) == 1
    assert parsed[0]["label"] == "Test Label"
    assert parsed[0]["value"] == "5.5"


@pytest.mark.unit
def test_parse_pdf_metrics_ignores_missing_label():
    """Metrics without labels should be skipped."""
    from app.services.report_pdf_extraction import _parse_pdf_metrics

    parsed = _parse_pdf_metrics(
        {"metrics": [{"value": "7"}, {"label": "Valid", "value": "8"}]}
    )
    assert len(parsed) == 1
    assert parsed[0]["label"] == "Valid"
    assert parsed[0]["value"] == "8"


@pytest.mark.unit
def test_parse_pdf_metrics_ignores_missing_value():
    """Metrics without values should be skipped."""
    from app.services.report_pdf_extraction import _parse_pdf_metrics

    parsed = _parse_pdf_metrics(
        {"metrics": [{"label": "NoValue"}, {"label": "HasValue", "value": "9"}]}
    )
    assert len(parsed) == 1
    assert parsed[0]["label"] == "HasValue"
    assert parsed[0]["value"] == "9"


@pytest.mark.unit
def test_parse_pdf_metrics_handles_empty_metrics():
    """Empty metrics list should return empty list."""
    from app.services.report_pdf_extraction import _parse_pdf_metrics

    parsed = _parse_pdf_metrics({"metrics": []})
    assert parsed == []


@pytest.mark.unit
def test_parse_pdf_metrics_handles_missing_metrics_key():
    """Missing metrics key should return empty list."""
    from app.services.report_pdf_extraction import _parse_pdf_metrics

    parsed = _parse_pdf_metrics({})
    assert parsed == []


@pytest.mark.unit
def test_parse_pdf_metrics_extracts_evidence():
    """Evidence quotes and page numbers should be extracted."""
    from app.services.report_pdf_extraction import _parse_pdf_metrics

    parsed = _parse_pdf_metrics({
        "metrics": [{
            "label": "Leadership",
            "value": "7.5",
            "evidence": {
                "quotes": ["Лидерство 7,5 баллов"],
                "page_numbers": [3, 4],
            }
        }]
    })
    assert len(parsed) == 1
    assert parsed[0]["label"] == "Leadership"
    assert parsed[0]["value"] == "7.5"
    assert parsed[0]["quotes"] == ["Лидерство 7,5 баллов"]
    assert parsed[0]["page_numbers"] == [3, 4]


@pytest.mark.unit
def test_parse_pdf_metrics_handles_missing_evidence():
    """Missing evidence should default to empty lists."""
    from app.services.report_pdf_extraction import _parse_pdf_metrics

    parsed = _parse_pdf_metrics({
        "metrics": [{"label": "Test", "value": "5"}]
    })
    assert len(parsed) == 1
    assert parsed[0]["quotes"] == []
    assert parsed[0]["page_numbers"] == []
