"""
REST API endpoints for participant management.

Provides CRUD operations and search/pagination functionality.
All endpoints require authentication (ACTIVE user).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.participant import (
    MessageResponse,
    ParticipantCreateRequest,
    ParticipantListResponse,
    ParticipantMetricResponse,
    ParticipantMetricsListResponse,
    ParticipantMetricUpdateRequest,
    ParticipantResponse,
    ParticipantSearchParams,
    ParticipantUpdateRequest,
)
from app.services.participant import ParticipantService

router = APIRouter(prefix="/participants", tags=["participants"])


@router.post("", response_model=ParticipantResponse, status_code=status.HTTP_201_CREATED)
async def create_participant(
    request: ParticipantCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ParticipantResponse:
    """
    Create a new participant.

    Requires: ACTIVE user (any role).

    Request body:
    - full_name: Full name (required, 1-255 chars)
    - birth_date: Birth date (optional)
    - external_id: External ID (optional, max 100 chars)

    Returns: Created participant with UUID and created_at timestamp.
    """
    service = ParticipantService(db)
    return await service.create_participant(request)


@router.get("", response_model=ParticipantListResponse)
async def search_participants(
    query: str | None = Query(None, description="Search by full_name (case-insensitive substring)"),
    external_id: str | None = Query(None, description="Filter by exact external_id match"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(20, ge=1, le=100, description="Page size (max 100)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ParticipantListResponse:
    """
    Search/list participants with pagination.

    Requires: ACTIVE user (any role).

    Query parameters:
    - query: Substring search on full_name (case-insensitive)
    - external_id: Exact match on external_id
    - page: Page number (default: 1)
    - size: Page size (default: 20, max: 100)

    Results are sorted deterministically by (full_name ASC, id ASC).

    Returns: Paginated list with items, total count, page info.
    """
    params = ParticipantSearchParams(query=query, external_id=external_id, page=page, size=size)
    service = ParticipantService(db)
    return await service.search_participants(params)


@router.get("/{participant_id}", response_model=ParticipantResponse)
async def get_participant(
    participant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ParticipantResponse:
    """
    Get a participant by ID.

    Requires: ACTIVE user (any role).

    Path parameter:
    - participant_id: UUID of the participant

    Returns: Participant details.
    Raises: 404 if participant not found.
    """
    service = ParticipantService(db)
    participant = await service.get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    return participant


@router.put("/{participant_id}", response_model=ParticipantResponse)
async def update_participant(
    participant_id: UUID,
    request: ParticipantUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ParticipantResponse:
    """
    Update a participant.

    Requires: ACTIVE user (any role).

    Path parameter:
    - participant_id: UUID of the participant

    Request body (all fields optional):
    - full_name: New full name
    - birth_date: New birth date
    - external_id: New external ID

    Returns: Updated participant.
    Raises: 404 if participant not found.
    """
    service = ParticipantService(db)
    participant = await service.update_participant(participant_id, request)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    return participant


@router.delete("/{participant_id}", response_model=MessageResponse)
async def delete_participant(
    participant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MessageResponse:
    """
    Delete a participant.

    Requires: ACTIVE user (any role).

    Path parameter:
    - participant_id: UUID of the participant

    Returns: Success message.
    Raises: 404 if participant not found.

    Note: Cascades to related reports due to FK constraints.
    """
    service = ParticipantService(db)
    deleted = await service.delete_participant(participant_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    return MessageResponse(message="Participant deleted successfully")


# Participant Metrics Endpoints

@router.get("/{participant_id}/metrics", response_model=ParticipantMetricsListResponse)
async def get_participant_metrics(
    participant_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ParticipantMetricsListResponse:
    """
    Get all actual metrics for a participant.

    Returns the latest confirmed value for each metric code,
    independent of specific reports.

    Requires: ACTIVE user (any role).

    Returns: List of participant metrics with values, confidence, and update timestamps.
    """
    from datetime import datetime

    from app.repositories.metric import MetricDefRepository
    from app.repositories.participant_metric import ParticipantMetricRepository

    service = ParticipantService(db)
    participant = await service.get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

    metric_repo = ParticipantMetricRepository(db)
    metrics = await metric_repo.list_by_participant(participant_id)
    by_code = {m.metric_code: m for m in metrics}

    metric_def_repo = MetricDefRepository(db)
    metric_defs = await metric_def_repo.list_all(active_only=True)

    # Fill missing metrics with synthetic zeros for complete UI coverage
    response_items: list[ParticipantMetricResponse] = []
    for md in metric_defs:
        existing = by_code.get(md.code)
        if existing:
            response_items.append(ParticipantMetricResponse.model_validate(existing))
        else:
            response_items.append(
                ParticipantMetricResponse(
                    metric_code=md.code,
                    value=0.0,
                    confidence=None,
                    last_source_report_id=None,
                    updated_at=participant.created_at if hasattr(participant, "created_at") else datetime.utcnow(),
                )
            )

    return ParticipantMetricsListResponse(
        participant_id=participant_id,
        metrics=response_items,
        total=len(response_items),
    )


@router.put(
    "/{participant_id}/metrics/{metric_code}",
    response_model=ParticipantMetricResponse,
)
async def update_participant_metric(
    participant_id: UUID,
    metric_code: str,
    request: ParticipantMetricUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ParticipantMetricResponse:
    """
    Manually update a participant metric value.

    Allows admin to manually correct or set metric values.
    This is useful for manual data entry or corrections.

    Requires: ACTIVE user (any role).

    Request body:
    - value: Metric value (range 1-10)
    - confidence: Optional confidence score (0-1)

    Returns: Updated metric with new value and timestamp.
    """
    from decimal import Decimal

    from app.repositories.participant_metric import ParticipantMetricRepository

    service = ParticipantService(db)
    participant = await service.get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

    metric_repo = ParticipantMetricRepository(db)
    metric = await metric_repo.update_value(
        participant_id=participant_id,
        metric_code=metric_code,
        value=Decimal(str(request.value)),
        confidence=Decimal(str(request.confidence)) if request.confidence else None,
    )

    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metric '{metric_code}' not found for participant {participant_id}",
        )

    return ParticipantMetricResponse.model_validate(metric)
