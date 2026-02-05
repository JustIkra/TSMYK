"""
Scoring router.

Endpoints for participant scoring calculations and results.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_active_user, require_admin
from app.db.models import Participant, User
from app.db.session import get_db
from app.schemas.scoring import (
    BatchRecalculateRequest,
    BatchRecalculateResponse,
    RecalculateRequest,
    ScoringResultListResponse,
    ScoringResultResponse,
)
from app.services.scoring import ScoringService

router = APIRouter(prefix="/scoring", tags=["scoring"])


@router.get(
    "/participants/{participant_id}",
    response_model=ScoringResultListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_participant_scores(
    participant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_active_user),
) -> ScoringResultListResponse:
    """
    Get all scoring results for a participant.

    Returns scores for all weight tables that have been calculated.
    """
    # Get participant name
    result = await db.execute(
        select(Participant).where(Participant.id == participant_id)
    )
    participant = result.scalar_one_or_none()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant {participant_id} not found",
        )

    service = ScoringService(db)
    return await service.get_participant_scores_response(
        participant_id=participant_id,
        participant_name=participant.full_name,
    )


@router.post(
    "/participants/{participant_id}/recalculate",
    response_model=list[ScoringResultResponse],
    status_code=status.HTTP_200_OK,
)
async def recalculate_participant_scores(
    participant_id: uuid.UUID,
    request: RecalculateRequest | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[ScoringResultResponse]:
    """
    Recalculate scoring for a participant.

    If weight_table_ids is provided, only recalculates for those tables.
    Otherwise, recalculates for all weight tables.

    Requires ADMIN role.
    """
    # Verify participant exists
    result = await db.execute(
        select(Participant).where(Participant.id == participant_id)
    )
    participant = result.scalar_one_or_none()
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant {participant_id} not found",
        )

    service = ScoringService(db)
    weight_table_ids = request.weight_table_ids if request else None

    results = await service.recalculate_participant(
        participant_id=participant_id,
        weight_table_ids=weight_table_ids,
    )

    return [service._serialize(r) for r in results]


@router.post(
    "/participants/{participant_id}/calculate/{weight_table_id}",
    response_model=ScoringResultResponse,
    status_code=status.HTTP_200_OK,
)
async def calculate_single_score(
    participant_id: uuid.UUID,
    weight_table_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> ScoringResultResponse:
    """
    Calculate or recalculate score for a specific participant and weight table.

    Requires ADMIN role.
    """
    # Verify participant exists
    result = await db.execute(
        select(Participant).where(Participant.id == participant_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Participant {participant_id} not found",
        )

    service = ScoringService(db)
    try:
        scoring_result = await service.calculate_score(
            participant_id=participant_id,
            weight_table_id=weight_table_id,
        )
        return service._serialize(scoring_result)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/batch/recalculate",
    response_model=BatchRecalculateResponse,
    status_code=status.HTTP_200_OK,
)
async def batch_recalculate(
    request: BatchRecalculateRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> BatchRecalculateResponse:
    """
    Batch recalculate scoring for multiple participants and/or weight tables.

    If participant_ids is None, calculates for all participants.
    If weight_table_ids is None, calculates for all weight tables.

    Requires ADMIN role.
    """
    from app.repositories.weight_table import WeightTableRepository

    service = ScoringService(db)
    weight_repo = WeightTableRepository(db)

    # Get weight tables
    if request.weight_table_ids:
        weight_tables = []
        for wt_id in request.weight_table_ids:
            wt = await weight_repo.get_by_id(wt_id)
            if wt:
                weight_tables.append(wt)
    else:
        weight_tables = await weight_repo.list_all()

    # Get participants
    if request.participant_ids:
        participant_ids = request.participant_ids
    else:
        result = await db.execute(select(Participant.id))
        participant_ids = [row[0] for row in result.fetchall()]

    total_calculated = 0
    errors = []

    for wt in weight_tables:
        count, wt_errors = await service.recalculate_all_for_weight_table(
            weight_table_id=wt.id,
            participant_ids=participant_ids,
        )
        total_calculated += count
        errors.extend(wt_errors)

    return BatchRecalculateResponse(
        total_calculated=total_calculated,
        errors=errors,
    )
