"""
Unit tests for RAG mapping service logic.

Tests the text normalization utility function.
"""

import pytest


@pytest.mark.unit
def test_norm_function():
    """Test text normalization function.

    _norm uses Title Case because indexed metric texts are stored in Title Case,
    and embedding similarity is significantly higher when query and indexed text
    have the same case.
    """
    from app.services.report_rag_mapping import _norm

    assert _norm("  hello   world  ") == "Hello World"
    assert _norm("Test\n\tString") == "Test String"
    assert _norm("already_normalized") == "Already_Normalized"
