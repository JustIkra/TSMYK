"""
Tests for ParticipantMetricRepository duplicate-resolution logic.

When multiple reports produce the same metric_code, we keep the "best" value:
1) higher value
2) on tie, higher confidence (NULL treated as 0)
3) on tie, more recent report.uploaded_at
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FileRef, Participant, Report
from app.repositories.participant_metric import ParticipantMetricRepository

pytestmark = [pytest.mark.asyncio]


@pytest_asyncio.fixture
async def participant(db_session: AsyncSession) -> Participant:
    participant = Participant(
        id=uuid.uuid4(),
        full_name="Priority Test Participant",
        birth_date=None,
        external_id=f"TEST-PRIORITY-{uuid.uuid4().hex[:8]}",
        created_at=datetime.now(UTC),
    )
    db_session.add(participant)
    await db_session.commit()
    await db_session.refresh(participant)
    return participant


async def _create_report_id(db_session: AsyncSession, participant_id: uuid.UUID, uploaded_at: datetime) -> uuid.UUID:
    file_ref = FileRef(
        id=uuid.uuid4(),
        storage="LOCAL",
        bucket="local",
        key=f"reports/{participant_id}/{uuid.uuid4()}/original.pdf",
        filename="test_report.pdf",
        mime="application/pdf",
        size_bytes=123,
        created_at=uploaded_at,
    )
    report_id = uuid.uuid4()

    # Use Core INSERT with explicit columns to be resilient to schema drift in local test DB.
    await db_session.execute(
        insert(FileRef).values(
            id=file_ref.id,
            storage=file_ref.storage,
            bucket=file_ref.bucket,
            key=file_ref.key,
            filename=file_ref.filename,
            mime=file_ref.mime,
            size_bytes=file_ref.size_bytes,
            created_at=file_ref.created_at,
        )
    )
    await db_session.execute(
        insert(Report).values(
            id=report_id,
            participant_id=participant_id,
            status="UPLOADED",
            file_ref_id=file_ref.id,
            uploaded_at=uploaded_at,
        )
    )
    await db_session.commit()
    return report_id


@pytest.mark.unit
async def test_upsert_prefers_higher_value_then_confidence_then_uploaded_at(
    db_session: AsyncSession, participant: Participant
):
    repo = ParticipantMetricRepository(db_session)

    t1 = datetime.now(UTC) - timedelta(days=2)
    t2 = datetime.now(UTC) - timedelta(days=1)

    report_old_id = await _create_report_id(db_session, participant.id, uploaded_at=t1)
    report_new_id = await _create_report_id(db_session, participant.id, uploaded_at=t2)

    # Seed with an initial value
    metric = await repo.upsert(
        participant_id=participant.id,
        metric_code="competency_1",
        value=Decimal("6.0"),
        confidence=Decimal("0.5"),
        source_report_id=report_old_id,
    )
    assert Decimal(str(metric.value)) == Decimal("6")
    assert metric.last_source_report_id == report_old_id

    # Worse value should not replace, even with higher confidence and newer report
    metric = await repo.upsert(
        participant_id=participant.id,
        metric_code="competency_1",
        value=Decimal("5.0"),
        confidence=Decimal("0.9"),
        source_report_id=report_new_id,
    )
    assert Decimal(str(metric.value)) == Decimal("6")
    assert metric.last_source_report_id == report_old_id

    # Same value + higher confidence should replace
    metric = await repo.upsert(
        participant_id=participant.id,
        metric_code="competency_1",
        value=Decimal("6.0"),
        confidence=Decimal("0.8"),
        source_report_id=report_new_id,
    )
    assert Decimal(str(metric.value)) == Decimal("6")
    assert Decimal(str(metric.confidence)) == Decimal("0.8")
    assert metric.last_source_report_id == report_new_id

    # Same value + same confidence + older report should not replace
    metric = await repo.upsert(
        participant_id=participant.id,
        metric_code="competency_1",
        value=Decimal("6.0"),
        confidence=Decimal("0.8"),
        source_report_id=report_old_id,
    )
    assert metric.last_source_report_id == report_new_id
