"""Tests for evidence-based value verification in PDF extraction."""

import pytest


def _verify(value: str, quotes: list[str]) -> bool:
    """Helper to test _evidence_contains_value function."""
    from app.services.report_pdf_extraction import _evidence_contains_value
    return _evidence_contains_value(value, quotes)


@pytest.mark.unit
def test_evidence_contains_value_accepts_decimal_comma_and_dot():
    """Value 7.5 should match evidence containing 7,5 and vice versa."""
    assert _verify("7.5", ["Лидерство 7,5"]) is True
    assert _verify("7,5", ["Лидерство 7.5"]) is True


@pytest.mark.unit
def test_evidence_contains_value_rejects_missing_value():
    """Value not present in evidence should be rejected."""
    assert _verify("8", ["Лидерство семь"]) is False
    assert _verify("9.5", ["Результат отличный"]) is False


@pytest.mark.unit
def test_evidence_contains_value_handles_whitespace():
    """Whitespace normalization should not affect matching."""
    assert _verify("5", ["Метрика  5   баллов"]) is True
    assert _verify("5", ["Метрика\n5\tбаллов"]) is True


@pytest.mark.unit
def test_evidence_contains_value_handles_multiple_quotes():
    """Value should be found if present in any quote."""
    quotes = ["Первая цитата без числа", "Вторая цитата с 8 баллами"]
    assert _verify("8", quotes) is True
    assert _verify("9", quotes) is False


@pytest.mark.unit
def test_evidence_contains_value_exact_number_match():
    """Value 8 should not match 8.5 or 18."""
    assert _verify("8", ["Результат 8.5"]) is False  # 8 != 8.5
    assert _verify("8", ["Результат 18"]) is False   # 8 != 18
    assert _verify("8", ["Результат 8 баллов"]) is True


@pytest.mark.unit
def test_evidence_contains_value_decimal_match():
    """Decimal values should match correctly."""
    assert _verify("8.5", ["Результат 8.5"]) is True
    assert _verify("8.5", ["Результат 8,5 баллов"]) is True
    assert _verify("8.5", ["Результат 8"]) is False  # 8.5 != 8


@pytest.mark.unit
def test_evidence_contains_value_empty_quotes():
    """Empty quotes should return False."""
    assert _verify("5", []) is False
    assert _verify("5", [""]) is False
