"""
Tests for scoring service and API (S2-02, S2-03, S2-06).

Verifies:
- Correct calculation of professional fitness scores
- Generation of strengths and development areas
- Scoring history retrieval for participants
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.db.models import Report
from app.repositories.metric import ExtractedMetricRepository, MetricDefRepository
from app.repositories.participant import ParticipantRepository
from app.repositories.prof_activity import ProfActivityRepository
from app.repositories.scoring_result import ScoringResultRepository
from app.services.scoring import ScoringService

# Fixtures



# Service Tests

@pytest.mark.asyncio
async def test_calculate_score__no_active_weight_table__raises_error(
    db_session, participant_with_metrics
):
    """
    Test that missing active weight table raises a ValueError.
    """
    participant, _ = participant_with_metrics

    # Use a prof activity code that doesn't exist
    scoring_service = ScoringService(db_session)

    with pytest.raises(ValueError, match="Professional activity .* not found"):
        await scoring_service.calculate_score(
            participant_id=participant.id, prof_activity_code="nonexistent_activity"
        )


# API Tests

# S2-03: Strengths/Dev Areas Tests




# BUG-02: Decimal Quantize Tests

# S2-06: Scoring History Tests



@pytest.mark.asyncio
async def test_api_get_scoring_history__no_results__returns_empty_list(
    client, db_session, participant_with_metrics, active_user_token
):
    """
    Test that empty list is returned when participant has no scoring results.
    """
    participant, _ = participant_with_metrics

    response = await client.get(
        f"/api/scoring/participants/{participant.id}/scores",
        cookies={"access_token": active_user_token},
    )

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert data["items"] == []


@pytest.mark.asyncio
async def test_api_get_scoring_history__participant_not_found__returns_404(
    client, active_user_token
):
    """
    Test that 404 is returned for non-existent participant.
    """
    non_existent_id = uuid4()

    response = await client.get(
        f"/api/scoring/participants/{non_existent_id}/scores",
        cookies={"access_token": active_user_token},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_get_scoring_history__unauthorized__returns_401(client, participant_with_metrics):
    """
    Test that unauthorized requests are rejected.
    """
    participant, _ = participant_with_metrics

    response = await client.get(f"/api/scoring/participants/{participant.id}/scores")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_get_scoring_history__with_recommendations__returns_structured_items(
    client, db_session, participant_with_metrics, active_user_token
):
    """
    Test that recommendations are returned as full objects in scoring history (AI-09 fix).
    """
    participant, _ = participant_with_metrics

    # Create a scoring result with recommendations
    scoring_repo = ScoringResultRepository(db_session)
    prof_activity_repo = ProfActivityRepository(db_session)

    # Get developer activity and its weight table
    prof_activity = await prof_activity_repo.get_by_code("developer")
    weight_table = await prof_activity_repo.get_active_weight_table(prof_activity.id)

    # Create scoring result with recommendations in dict format
    recommendations_data = [
        {"title": "Курс по стрессоустойчивости", "link_url": "https://example.com/stress", "priority": 1},
        {"title": "Тренинг по лидерству", "link_url": "https://example.com/leadership", "priority": 2},
        {"title": "Курс по расширению словарного запаса", "link_url": "", "priority": 3},
    ]

    scoring_result = await scoring_repo.create(
        participant_id=participant.id,
        weight_table_id=weight_table.id,
        score_pct=Decimal("65.50"),
        strengths=[],
        dev_areas=[],
        recommendations=recommendations_data,
        compute_notes="Test scoring with recommendations",
        recommendations_status="ready",
    )

    # Get scoring history via API
    response = await client.get(
        f"/api/participants/{participant.id}/scores",
        cookies={"access_token": active_user_token},
    )

    assert response.status_code == 200
    data = response.json()

    assert "results" in data
    assert len(data["results"]) == 1

    history_item = data["results"][0]
    assert "recommendations" in history_item
    assert history_item["recommendations"] is not None
    assert len(history_item["recommendations"]) == 3

    # Verify recommendations are returned as dicts with expected keys
    first_rec = history_item["recommendations"][0]
    assert set(first_rec.keys()) == {"title", "link_url", "priority"}
    assert first_rec["title"] == "Курс по стрессоустойчивости"
    assert history_item["recommendations_status"] == "ready"
    assert history_item["recommendations_error"] is None
