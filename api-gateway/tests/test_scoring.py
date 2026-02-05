"""
Tests for the scoring calculation module.

Tests cover:
- Base score calculation (weighted average)
- Penalty multiplier calculation
- Final score calculation
- Critical metrics with penalties
- API endpoints for scoring
- Auto-recalculation on metric updates
"""

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Participant, ParticipantMetric, ProfActivity, User, WeightTable
from app.repositories.participant_metric import ParticipantMetricRepository
from app.repositories.prof_activity import ProfActivityRepository
from app.repositories.weight_table import WeightTableRepository
from app.services.scoring import ScoringService

pytestmark = pytest.mark.asyncio


# Fixtures


@pytest_asyncio.fixture
async def prof_activity_scoring(db_session: AsyncSession) -> ProfActivity:
    """Create a professional activity for scoring tests."""
    repo = ProfActivityRepository(db_session)
    unique_code = f"scoring_test_{uuid.uuid4().hex[:8]}"
    activity = await repo.create(
        code=unique_code,
        name="Scoring Test Activity",
        description="Activity for testing scoring calculations",
    )
    return activity


@pytest_asyncio.fixture
async def participant_scoring(db_session: AsyncSession) -> Participant:
    """Create a participant for scoring tests."""
    participant = Participant(
        full_name="Test Scoring Participant",
        external_id=f"scoring_{uuid.uuid4().hex[:8]}",
    )
    db_session.add(participant)
    await db_session.commit()
    await db_session.refresh(participant)
    return participant


@pytest_asyncio.fixture
async def weight_table_with_penalties(
    db_session: AsyncSession,
    prof_activity_scoring: ProfActivity,
) -> WeightTable:
    """Create a weight table with critical metrics and penalties."""
    repo = WeightTableRepository(db_session)
    weights = [
        {
            "metric_code": "BP01",
            "weight": "0.3",
            "is_critical": True,
            "penalty": "0.30",
            "threshold": "6.0",
        },
        {
            "metric_code": "BP02",
            "weight": "0.3",
            "is_critical": True,
            "penalty": "0.25",
            "threshold": "5.0",
        },
        {
            "metric_code": "BP03",
            "weight": "0.2",
            "is_critical": False,
            "penalty": "0",
            "threshold": "6.0",
        },
        {
            "metric_code": "BP04",
            "weight": "0.2",
            "is_critical": False,
            "penalty": "0",
            "threshold": "6.0",
        },
    ]
    table = await repo.create(
        prof_activity_id=prof_activity_scoring.id,
        weights=weights,
        metadata={"version": "1.0", "test": True},
    )
    return table


@pytest_asyncio.fixture
async def weight_table_simple(
    db_session: AsyncSession,
    prof_activity_scoring: ProfActivity,
) -> WeightTable:
    """Create a simple weight table without penalties."""
    repo = WeightTableRepository(db_session)
    # Delete existing table for this activity first
    existing = await repo.get_by_activity(prof_activity_scoring.id)
    if existing:
        await db_session.delete(existing)
        await db_session.commit()

    weights = [
        {"metric_code": "M1", "weight": "0.5", "is_critical": False, "penalty": "0", "threshold": "6.0"},
        {"metric_code": "M2", "weight": "0.5", "is_critical": False, "penalty": "0", "threshold": "6.0"},
    ]
    table = await repo.create(
        prof_activity_id=prof_activity_scoring.id,
        weights=weights,
        metadata=None,
    )
    return table


@pytest_asyncio.fixture
async def participant_with_metrics(
    db_session: AsyncSession,
    participant_scoring: Participant,
) -> Participant:
    """Create participant metrics for scoring tests."""
    repo = ParticipantMetricRepository(db_session)

    # Create metrics for the participant
    metrics = [
        ("BP01", Decimal("7.5")),  # Above threshold
        ("BP02", Decimal("4.0")),  # Below threshold (5.0) - penalty applies
        ("BP03", Decimal("8.0")),
        ("BP04", Decimal("6.5")),
    ]

    for metric_code, value in metrics:
        metric = ParticipantMetric(
            participant_id=participant_scoring.id,
            metric_code=metric_code,
            value=value,
            confidence=Decimal("0.95"),
        )
        db_session.add(metric)

    await db_session.commit()
    return participant_scoring


# Test: Base score calculation


async def test_base_score_calculation(
    db_session: AsyncSession,
    participant_scoring: Participant,
    weight_table_simple: WeightTable,
) -> None:
    """Test that base score is calculated as weighted average."""
    # Setup metrics
    repo = ParticipantMetricRepository(db_session)
    await db_session.execute(
        ParticipantMetric.__table__.insert().values([
            {"id": uuid.uuid4(), "participant_id": participant_scoring.id, "metric_code": "M1", "value": Decimal("8.0")},
            {"id": uuid.uuid4(), "participant_id": participant_scoring.id, "metric_code": "M2", "value": Decimal("6.0")},
        ])
    )
    await db_session.commit()

    # Calculate score
    service = ScoringService(db_session)
    result = await service.calculate_score(
        participant_id=participant_scoring.id,
        weight_table_id=weight_table_simple.id,
    )

    # Expected: (8.0 * 0.5 + 6.0 * 0.5) / 1.0 = 7.0
    assert result.base_score == Decimal("7.00")
    assert result.penalty_multiplier == Decimal("1.0000")
    assert result.final_score == Decimal("7.00")


async def test_penalty_multiplier_calculation(
    db_session: AsyncSession,
    participant_with_metrics: Participant,
    weight_table_with_penalties: WeightTable,
) -> None:
    """Test that penalty multiplier is calculated correctly for critical metrics below threshold."""
    service = ScoringService(db_session)
    result = await service.calculate_score(
        participant_id=participant_with_metrics.id,
        weight_table_id=weight_table_with_penalties.id,
    )

    # BP02 is below threshold (4.0 < 5.0), penalty 0.25 applies
    # BP01 is above threshold (7.5 >= 6.0), no penalty
    # Expected penalty_multiplier: (1 - 0.25) = 0.75
    assert result.penalty_multiplier == Decimal("0.7500")


async def test_final_score_with_penalties(
    db_session: AsyncSession,
    participant_with_metrics: Participant,
    weight_table_with_penalties: WeightTable,
) -> None:
    """Test that final score = base_score * penalty_multiplier."""
    service = ScoringService(db_session)
    result = await service.calculate_score(
        participant_id=participant_with_metrics.id,
        weight_table_id=weight_table_with_penalties.id,
    )

    # Verify final_score = base_score * penalty_multiplier
    expected_final = result.base_score * result.penalty_multiplier
    assert abs(float(result.final_score) - float(expected_final)) < 0.01


async def test_penalties_applied_tracking(
    db_session: AsyncSession,
    participant_with_metrics: Participant,
    weight_table_with_penalties: WeightTable,
) -> None:
    """Test that applied penalties are tracked correctly."""
    service = ScoringService(db_session)
    result = await service.calculate_score(
        participant_id=participant_with_metrics.id,
        weight_table_id=weight_table_with_penalties.id,
    )

    # Should have 1 penalty (BP02)
    assert result.penalties_applied is not None
    assert len(result.penalties_applied) == 1
    assert result.penalties_applied[0]["metric_code"] == "BP02"
    assert Decimal(result.penalties_applied[0]["value"]) == Decimal("4.0")
    assert Decimal(result.penalties_applied[0]["threshold"]) == Decimal("5.0")
    assert Decimal(result.penalties_applied[0]["penalty"]) == Decimal("0.25")


async def test_no_penalties_when_all_above_threshold(
    db_session: AsyncSession,
    participant_scoring: Participant,
    weight_table_with_penalties: WeightTable,
) -> None:
    """Test that no penalties are applied when all critical metrics are above threshold."""
    # Create metrics all above thresholds
    metrics = [
        ("BP01", Decimal("7.0")),  # >= 6.0
        ("BP02", Decimal("6.0")),  # >= 5.0
        ("BP03", Decimal("8.0")),
        ("BP04", Decimal("7.0")),
    ]
    for metric_code, value in metrics:
        metric = ParticipantMetric(
            participant_id=participant_scoring.id,
            metric_code=metric_code,
            value=value,
            confidence=Decimal("0.9"),
        )
        db_session.add(metric)
    await db_session.commit()

    service = ScoringService(db_session)
    result = await service.calculate_score(
        participant_id=participant_scoring.id,
        weight_table_id=weight_table_with_penalties.id,
    )

    assert result.penalty_multiplier == Decimal("1.0000")
    assert result.penalties_applied is None or len(result.penalties_applied) == 0
    assert result.final_score == result.base_score


async def test_multiple_penalties_multiply(
    db_session: AsyncSession,
    participant_scoring: Participant,
    weight_table_with_penalties: WeightTable,
) -> None:
    """Test that multiple penalties are multiplied together."""
    # Create metrics with both critical below threshold
    metrics = [
        ("BP01", Decimal("4.0")),  # < 6.0, penalty 0.30
        ("BP02", Decimal("3.0")),  # < 5.0, penalty 0.25
        ("BP03", Decimal("8.0")),
        ("BP04", Decimal("7.0")),
    ]
    for metric_code, value in metrics:
        metric = ParticipantMetric(
            participant_id=participant_scoring.id,
            metric_code=metric_code,
            value=value,
            confidence=Decimal("0.9"),
        )
        db_session.add(metric)
    await db_session.commit()

    service = ScoringService(db_session)
    result = await service.calculate_score(
        participant_id=participant_scoring.id,
        weight_table_id=weight_table_with_penalties.id,
    )

    # Expected: (1 - 0.30) * (1 - 0.25) = 0.70 * 0.75 = 0.525
    expected_multiplier = Decimal("0.70") * Decimal("0.75")
    assert abs(float(result.penalty_multiplier) - float(expected_multiplier)) < 0.001
    assert len(result.penalties_applied) == 2


async def test_missing_metrics_are_skipped(
    db_session: AsyncSession,
    participant_scoring: Participant,
    weight_table_with_penalties: WeightTable,
) -> None:
    """Test that missing metrics are skipped in calculations."""
    # Only create one metric
    metric = ParticipantMetric(
        participant_id=participant_scoring.id,
        metric_code="BP01",
        value=Decimal("8.0"),
        confidence=Decimal("0.9"),
    )
    db_session.add(metric)
    await db_session.commit()

    service = ScoringService(db_session)
    result = await service.calculate_score(
        participant_id=participant_scoring.id,
        weight_table_id=weight_table_with_penalties.id,
    )

    # Should calculate based only on available metric
    assert result.metrics_used is not None
    assert len(result.metrics_used) == 1
    assert result.metrics_used[0]["metric_code"] == "BP01"


# Test: API endpoints


async def test_get_participant_scores_api(
    client: AsyncClient,
    active_user: User,
    participant_with_metrics: Participant,
    weight_table_with_penalties: WeightTable,
    db_session: AsyncSession,
) -> None:
    """Test GET /api/scoring/participants/{id} endpoint."""
    from tests.conftest import get_auth_header

    # First calculate a score
    service = ScoringService(db_session)
    await service.calculate_score(
        participant_id=participant_with_metrics.id,
        weight_table_id=weight_table_with_penalties.id,
    )

    response = await client.get(
        f"/api/scoring/participants/{participant_with_metrics.id}",
        headers=get_auth_header(active_user),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["participant_id"] == str(participant_with_metrics.id)
    assert len(data["results"]) >= 1


async def test_recalculate_participant_requires_admin(
    client: AsyncClient,
    active_user: User,
    participant_scoring: Participant,
) -> None:
    """Regular users should not be able to recalculate scores."""
    from tests.conftest import get_auth_header

    response = await client.post(
        f"/api/scoring/participants/{participant_scoring.id}/recalculate",
        headers=get_auth_header(active_user),
    )

    assert response.status_code == 403


async def test_recalculate_participant_as_admin(
    client: AsyncClient,
    admin_user: User,
    participant_with_metrics: Participant,
    weight_table_with_penalties: WeightTable,
) -> None:
    """Admins should be able to recalculate scores."""
    from tests.conftest import get_auth_header

    response = await client.post(
        f"/api/scoring/participants/{participant_with_metrics.id}/recalculate",
        headers=get_auth_header(admin_user),
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


async def test_calculate_single_score_api(
    client: AsyncClient,
    admin_user: User,
    participant_with_metrics: Participant,
    weight_table_with_penalties: WeightTable,
) -> None:
    """Test calculating a single score via API."""
    from tests.conftest import get_auth_header

    response = await client.post(
        f"/api/scoring/participants/{participant_with_metrics.id}/calculate/{weight_table_with_penalties.id}",
        headers=get_auth_header(admin_user),
    )

    assert response.status_code == 200
    data = response.json()
    assert "base_score" in data
    assert "penalty_multiplier" in data
    assert "final_score" in data


async def test_get_scores_for_nonexistent_participant(
    client: AsyncClient,
    active_user: User,
) -> None:
    """Test that 404 is returned for nonexistent participant."""
    from tests.conftest import get_auth_header

    fake_id = uuid.uuid4()
    response = await client.get(
        f"/api/scoring/participants/{fake_id}",
        headers=get_auth_header(active_user),
    )

    assert response.status_code == 404


# Test: Score clamping


async def test_score_clamped_to_valid_range(
    db_session: AsyncSession,
    participant_scoring: Participant,
    weight_table_simple: WeightTable,
) -> None:
    """Test that scores are clamped to 0-10 range."""
    # Create metrics with extreme values
    metrics = [
        ("M1", Decimal("10.0")),
        ("M2", Decimal("10.0")),
    ]
    for metric_code, value in metrics:
        metric = ParticipantMetric(
            participant_id=participant_scoring.id,
            metric_code=metric_code,
            value=value,
            confidence=Decimal("1.0"),
        )
        db_session.add(metric)
    await db_session.commit()

    service = ScoringService(db_session)
    result = await service.calculate_score(
        participant_id=participant_scoring.id,
        weight_table_id=weight_table_simple.id,
    )

    assert result.base_score <= Decimal("10.00")
    assert result.final_score <= Decimal("10.00")
    assert result.base_score >= Decimal("0.00")
    assert result.final_score >= Decimal("0.00")


# Test: Upsert behavior


async def test_scoring_result_upsert(
    db_session: AsyncSession,
    participant_with_metrics: Participant,
    weight_table_with_penalties: WeightTable,
) -> None:
    """Test that recalculating updates existing result."""
    service = ScoringService(db_session)

    # Calculate first time
    result1 = await service.calculate_score(
        participant_id=participant_with_metrics.id,
        weight_table_id=weight_table_with_penalties.id,
    )
    result1_id = result1.id

    # Calculate again
    result2 = await service.calculate_score(
        participant_id=participant_with_metrics.id,
        weight_table_id=weight_table_with_penalties.id,
    )

    # Should update existing, not create new
    assert result2.id == result1_id
