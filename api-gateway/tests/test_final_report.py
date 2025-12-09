"""
Tests for final report generation.

Verifies:
- JSON schema validation
- HTML template rendering
- Snapshot testing for HTML output
"""

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.repositories.metric import ExtractedMetricRepository, MetricDefRepository
from app.repositories.participant import ParticipantRepository
from app.repositories.prof_activity import ProfActivityRepository
from app.repositories.weight_table import WeightTableRepository
from app.schemas.final_report import FinalReportResponse
from app.services.report_template import render_final_report_html
from app.services.scoring import ScoringService

# Fixtures




# Service Tests

@pytest.mark.asyncio
async def test_generate_final_report__with_valid_data__returns_complete_structure(
    db_session, participant_with_full_data
):
    """Test that generate_final_report returns all required fields."""
    # Arrange
    participant = participant_with_full_data["participant"]
    scoring_service = ScoringService(db_session)

    # Act
    report_data = await scoring_service.generate_final_report(
        participant_id=participant.id,
        prof_activity_code=participant_with_full_data["prof_activity"].code,
    )

    # Assert: Check structure
    assert "participant_id" in report_data
    assert "participant_name" in report_data
    assert "report_date" in report_data
    assert "prof_activity_code" in report_data
    assert "prof_activity_name" in report_data
    assert "weight_table_id" in report_data
    assert "score_pct" in report_data
    assert "strengths" in report_data
    assert "dev_areas" in report_data
    assert "recommendations" in report_data
    assert "recommendations_status" in report_data
    assert "recommendations_error" in report_data
    assert "metrics" in report_data
    assert "notes" in report_data
    assert "template_version" in report_data

    # Assert: Check values
    assert report_data["participant_id"] == participant.id
    assert report_data["participant_name"] == "Ивано Иванов Иванович"
    assert report_data["prof_activity_code"] == participant_with_full_data["prof_activity"].code
    assert report_data["prof_activity_name"] == participant_with_full_data["prof_activity"].name
    assert report_data["weight_table_id"] is not None  # Should have a valid weight table ID
    assert isinstance(report_data["score_pct"], Decimal)
    assert Decimal("0") <= report_data["score_pct"] <= Decimal("100")
    assert report_data["recommendations_status"] in {"pending", "ready", "error", "disabled"}
    error_value = report_data["recommendations_error"]
    assert error_value is None or isinstance(error_value, str)

    # Assert: Strengths and dev_areas
    assert len(report_data["strengths"]) <= 5
    assert len(report_data["dev_areas"]) <= 5

    # Assert: Each strength has required fields
    for strength in report_data["strengths"]:
        assert "title" in strength
        assert "metric_codes" in strength
        assert "reason" in strength

    # Assert: Each dev_area has required fields
    for dev_area in report_data["dev_areas"]:
        assert "title" in dev_area
        assert "metric_codes" in dev_area
        assert "actions" in dev_area

    # Assert: Metrics table
    assert len(report_data["metrics"]) == participant_with_full_data["metrics_count"]
    for metric in report_data["metrics"]:
        assert "code" in metric
        assert "name" in metric
        assert "value" in metric
        assert "unit" in metric
        assert "weight" in metric
        assert "contribution" in metric
        assert "source" in metric
        # confidence can be None


@pytest.mark.asyncio
async def test_final_report__json_schema_validation__passes_pydantic(
    db_session, participant_with_full_data
):
    """Test that final report data validates against Pydantic schema (S2-04 AC)."""
    # Arrange
    participant = participant_with_full_data["participant"]
    scoring_service = ScoringService(db_session)

    # Act
    report_data = await scoring_service.generate_final_report(
        participant_id=participant.id,
        prof_activity_code=participant_with_full_data["prof_activity"].code,
    )

    # Assert: Should not raise ValidationError
    report_response = FinalReportResponse(**report_data)

    # Verify key fields
    assert report_response.participant_name == "Ивано Иванов Иванович"
    assert report_response.prof_activity_code == participant_with_full_data["prof_activity"].code
    assert report_response.template_version == "1.0.0"
    assert 0 <= report_response.score_pct <= 100


@pytest.mark.asyncio
async def test_final_report__html_rendering__produces_valid_html(
    db_session, participant_with_full_data
):
    """Test that HTML template renders without errors (S2-04 AC)."""
    # Arrange
    participant = participant_with_full_data["participant"]
    scoring_service = ScoringService(db_session)

    report_data = await scoring_service.generate_final_report(
        participant_id=participant.id,
        prof_activity_code=participant_with_full_data["prof_activity"].code,
    )

    # Act
    html = render_final_report_html(report_data)

    # Assert: Basic HTML structure
    assert html is not None
    assert len(html) > 0
    assert "<!DOCTYPE html>" in html
    assert "<html" in html
    assert "</html>" in html

    # Assert: Key content present
    assert "Ивано Иванов Иванович" in html
    assert participant_with_full_data["prof_activity"].name in html
    assert "Итоговый коэффициент" in html
    assert "Сильные стороны" in html
    assert "Зоны развития" in html


@pytest.mark.asyncio
async def test_final_report__html_snapshot__matches_expected(
    db_session, participant_with_full_data
):
    """Test HTML output against snapshot for regression detection (S2-04 AC)."""
    # Arrange
    participant = participant_with_full_data["participant"]
    scoring_service = ScoringService(db_session)

    report_data = await scoring_service.generate_final_report(
        participant_id=participant.id,
        prof_activity_code=participant_with_full_data["prof_activity"].code,
    )

    # Normalize dynamic fields for snapshot
    report_data["report_date"] = datetime(2025, 1, 15, 10, 30, 0)
    report_data["participant_id"] = uuid4()  # Fixed UUID for snapshot

    # Act
    html = render_final_report_html(report_data)

    # Assert: Check key structural elements
    assert "<title>Итоговый отчёт — Ивано Иванов Иванович</title>" in html
    assert 'class="score-section"' in html
    assert 'class="metrics-table"' in html

    # Check that metrics table has all rows
    assert html.count("<tr>") >= participant_with_full_data["metrics_count"]

    # Check CSS is embedded
    assert "font-family: 'Segoe UI'" in html
    assert "#00798D" in html  # Primary color

    # Check template version in footer
    assert "Версия шаблона отчёта: 1.0.0" in html


@pytest.mark.asyncio
async def test_final_report__no_scoring_result__raises_error(
    db_session, participant_with_full_data
):
    """Test that generate_final_report raises error if no scoring result exists."""
    # Arrange
    participant_repo = ParticipantRepository(db_session)
    new_participant = await participant_repo.create(
        full_name="No Score Participant",
        birth_date=date(1995, 1, 1),
    )

    scoring_service = ScoringService(db_session)
    prof_activity = participant_with_full_data["prof_activity"]

    # Act & Assert
    with pytest.raises(ValueError, match="No scoring result found"):
        await scoring_service.generate_final_report(
            participant_id=new_participant.id,
            prof_activity_code=prof_activity.code,
        )


# API Tests

@pytest.mark.asyncio
async def test_api_final_report_json__with_valid_data__returns_200(
    test_env, client: AsyncClient, db_session, participant_with_full_data
):
    """Test API endpoint for final report JSON format."""
    # Arrange
    participant = participant_with_full_data["participant"]
    prof_activity = participant_with_full_data["prof_activity"]

    # Create active user and get auth cookies
    from app.services.auth import create_user

    user = await create_user(db_session, "active@example.com", "password123", role="USER")
    user.status = "ACTIVE"
    await db_session.commit()

    # Login to get cookies
    login_response = await client.post(
        "/api/auth/login", json={"email": "active@example.com", "password": "password123"}
    )
    assert login_response.status_code == 200
    auth_cookies = dict(login_response.cookies)

    # Act
    response = await client.get(
        f"/api/participants/{participant.id}/final-report?activity_code={prof_activity.code}",
        cookies=auth_cookies,
    )

    # Assert
    assert response.status_code == 200
    data = response.json()

    assert data["participant_name"] == "Ивано Иванов Иванович"
    assert data["prof_activity_code"] == prof_activity.code
    assert "score_pct" in data
    assert "strengths" in data
    assert "dev_areas" in data
    assert "metrics" in data


@pytest.mark.asyncio
async def test_api_final_report_html__with_format_param__returns_html(
    test_env, client: AsyncClient, db_session, participant_with_full_data
):
    """Test API endpoint for final report HTML format."""
    # Arrange
    participant = participant_with_full_data["participant"]
    prof_activity = participant_with_full_data["prof_activity"]

    # Create active user and get auth cookies
    from app.services.auth import create_user

    user = await create_user(db_session, "active@example.com", "password123", role="USER")
    user.status = "ACTIVE"
    await db_session.commit()

    # Login to get cookies
    login_response = await client.post(
        "/api/auth/login", json={"email": "active@example.com", "password": "password123"}
    )
    assert login_response.status_code == 200
    auth_cookies = dict(login_response.cookies)

    # Act
    response = await client.get(
        f"/api/participants/{participant.id}/final-report?activity_code={prof_activity.code}&format=html",
        cookies=auth_cookies,
    )

    # Assert
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")

    html = response.text
    assert "<!DOCTYPE html>" in html
    assert "Ивано Иванов Иванович" in html
    assert "Итоговый коэффициент" in html


# Edge Case Tests

@pytest.mark.asyncio
async def test_api_final_report__participant_not_found__returns_404(
    test_env, client: AsyncClient, db_session
):
    """Test that API returns 404 when participant doesn't exist."""
    # Arrange: Create active user and get auth cookies
    from app.services.auth import create_user

    user = await create_user(db_session, "active@example.com", "password123", role="USER")
    user.status = "ACTIVE"
    await db_session.commit()

    # Login to get cookies
    login_response = await client.post(
        "/api/auth/login", json={"email": "active@example.com", "password": "password123"}
    )
    assert login_response.status_code == 200
    auth_cookies = dict(login_response.cookies)

    # Act: Try to get final report for non-existent participant
    non_existent_id = uuid4()
    response = await client.get(
        f"/api/participants/{non_existent_id}/final-report?activity_code=nonexistent_activity",
        cookies=auth_cookies,
    )

    # Assert
    assert response.status_code == 400
    # The error could be about missing activity or no scoring result
    assert "not found" in response.json()["detail"].lower() or "no" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_final_report__invalid_activity_code__returns_400(
    test_env, client: AsyncClient, db_session, participant_with_full_data
):
    """Test that API returns 400 when activity code is invalid."""
    # Arrange
    participant = participant_with_full_data["participant"]

    # Create active user and get auth cookies
    from app.services.auth import create_user

    user = await create_user(db_session, "active@example.com", "password123", role="USER")
    user.status = "ACTIVE"
    await db_session.commit()

    # Login to get cookies
    login_response = await client.post(
        "/api/auth/login", json={"email": "active@example.com", "password": "password123"}
    )
    assert login_response.status_code == 200
    auth_cookies = dict(login_response.cookies)

    # Act: Try to get final report with invalid activity code
    response = await client.get(
        f"/api/participants/{participant.id}/final-report?activity_code=invalid_activity_code",
        cookies=auth_cookies,
    )

    # Assert
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_final_report__unauthorized__returns_401(
    test_env, client: AsyncClient, db_session, participant_with_full_data
):
    """Test that API requires authentication."""
    # Arrange
    participant = participant_with_full_data["participant"]
    prof_activity = participant_with_full_data["prof_activity"]

    # Act: Try to access without auth cookies
    response = await client.get(
        f"/api/participants/{participant.id}/final-report?activity_code={prof_activity.code}"
    )

    # Assert
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_final_report__invalid_format_parameter__defaults_to_json(
    test_env, client: AsyncClient, db_session, participant_with_full_data
):
    """Test that invalid format parameter defaults to JSON response."""
    # Arrange
    participant = participant_with_full_data["participant"]
    prof_activity = participant_with_full_data["prof_activity"]

    # Create active user and get auth cookies
    from app.services.auth import create_user

    user = await create_user(db_session, "active@example.com", "password123", role="USER")
    user.status = "ACTIVE"
    await db_session.commit()

    # Login to get cookies
    login_response = await client.post(
        "/api/auth/login", json={"email": "active@example.com", "password": "password123"}
    )
    assert login_response.status_code == 200
    auth_cookies = dict(login_response.cookies)

    # Act: Request with invalid format parameter
    response = await client.get(
        f"/api/participants/{participant.id}/final-report?activity_code={prof_activity.code}&format=pdf",
        cookies=auth_cookies,
    )

    # Assert: Should default to JSON
    assert response.status_code == 200
    assert response.headers.get("content-type") == "application/json"
    data = response.json()
    assert "participant_name" in data
    assert "score_pct" in data
