"""
Service layer for scoring calculations.

Implements the scoring formula:
1. BaseScore = Σ(w_i × x_i) / Σ(w_i)
2. PenaltyMultiplier = Π(1 - penalty_i) for critical metrics where x_i < threshold_i
3. FinalScore = BaseScore × PenaltyMultiplier
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Participant, ScoringResult, WeightTable
from app.repositories.participant_metric import ParticipantMetricRepository
from app.repositories.scoring_result import ScoringResultRepository
from app.repositories.weight_table import WeightTableRepository
from app.schemas.scoring import (
    MetricUsed,
    PenaltyApplied,
    ScoringResultListResponse,
    ScoringResultResponse,
)

logger = logging.getLogger(__name__)


class ScoringService:
    """Business logic for calculating participant scores based on weight tables."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.scoring_repo = ScoringResultRepository(db)
        self.weight_repo = WeightTableRepository(db)
        self.metric_repo = ParticipantMetricRepository(db)

    async def calculate_score(
        self,
        participant_id: UUID,
        weight_table_id: UUID,
    ) -> ScoringResult:
        """
        Calculate and store scoring result for a participant against a weight table.

        Formula:
        1. BaseScore = Σ(w_i × x_i) / Σ(w_i)
        2. PenaltyMultiplier = Π(1 - penalty_i) for critical metrics where x_i < threshold_i
        3. FinalScore = BaseScore × PenaltyMultiplier

        Returns:
            ScoringResult with calculated scores
        """
        # Get weight table
        weight_table = await self.weight_repo.get_by_id(weight_table_id)
        if not weight_table:
            raise ValueError(f"Weight table {weight_table_id} not found")

        # Get participant metrics
        participant_metrics = await self.metric_repo.get_metrics_dict(participant_id)

        # Parse weights from JSONB
        weights = weight_table.weights  # list[dict]

        # Calculate base score and collect penalties
        weighted_sum = Decimal("0")
        total_weight = Decimal("0")
        penalties_applied: list[dict[str, Any]] = []
        metrics_used: list[dict[str, Any]] = []

        for weight_entry in weights:
            metric_code = weight_entry["metric_code"]
            weight = Decimal(str(weight_entry["weight"]))
            is_critical = weight_entry.get("is_critical", False)
            penalty = Decimal(str(weight_entry.get("penalty", "0")))
            threshold = Decimal(str(weight_entry.get("threshold", "6.0")))

            # Get participant value for this metric
            value = participant_metrics.get(metric_code)
            if value is None:
                # Skip metrics that participant doesn't have
                logger.debug(f"Participant {participant_id} missing metric {metric_code}")
                continue

            value = Decimal(str(value))
            weighted_value = weight * value
            weighted_sum += weighted_value
            total_weight += weight

            metrics_used.append({
                "metric_code": metric_code,
                "value": str(value),
                "weight": str(weight),
                "weighted_value": str(weighted_value),
            })

            # Check for penalty on critical metrics
            if is_critical and value < threshold and penalty > 0:
                penalties_applied.append({
                    "metric_code": metric_code,
                    "value": str(value),
                    "threshold": str(threshold),
                    "penalty": str(penalty),
                })

        # Calculate base score
        if total_weight > 0:
            base_score = weighted_sum / total_weight
        else:
            base_score = Decimal("0")

        # Calculate penalty multiplier: Π(1 - penalty_i)
        penalty_multiplier = Decimal("1")
        for penalty_entry in penalties_applied:
            penalty_value = Decimal(penalty_entry["penalty"])
            penalty_multiplier *= (Decimal("1") - penalty_value)

        # Calculate final score
        final_score = base_score * penalty_multiplier

        # Clamp to 0-10 range
        base_score = max(Decimal("0"), min(Decimal("10"), base_score))
        final_score = max(Decimal("0"), min(Decimal("10"), final_score))

        # Round to 2 decimal places
        base_score = base_score.quantize(Decimal("0.01"))
        penalty_multiplier = penalty_multiplier.quantize(Decimal("0.0001"))
        final_score = final_score.quantize(Decimal("0.01"))

        logger.info(
            f"Calculated score for participant {participant_id} with weight_table {weight_table_id}: "
            f"base={base_score}, multiplier={penalty_multiplier}, final={final_score}, "
            f"penalties={len(penalties_applied)}"
        )

        # Store result
        return await self.scoring_repo.upsert(
            participant_id=participant_id,
            weight_table_id=weight_table_id,
            base_score=base_score,
            penalty_multiplier=penalty_multiplier,
            final_score=final_score,
            penalties_applied=penalties_applied if penalties_applied else None,
            metrics_used=metrics_used if metrics_used else None,
        )

    async def get_participant_scores(
        self,
        participant_id: UUID,
    ) -> list[ScoringResult]:
        """Get all scoring results for a participant."""
        return await self.scoring_repo.list_by_participant(participant_id)

    async def recalculate_participant(
        self,
        participant_id: UUID,
        weight_table_ids: list[UUID] | None = None,
    ) -> list[ScoringResult]:
        """
        Recalculate scoring for a participant.

        Args:
            participant_id: Participant UUID
            weight_table_ids: Specific tables to recalculate. If None, uses all tables.

        Returns:
            List of updated ScoringResult objects
        """
        if weight_table_ids:
            tables = []
            for wt_id in weight_table_ids:
                table = await self.weight_repo.get_by_id(wt_id)
                if table:
                    tables.append(table)
        else:
            tables = await self.weight_repo.list_all()

        results = []
        for table in tables:
            try:
                result = await self.calculate_score(participant_id, table.id)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to calculate score for {participant_id}/{table.id}: {e}")

        return results

    async def recalculate_all_for_weight_table(
        self,
        weight_table_id: UUID,
        participant_ids: list[UUID] | None = None,
    ) -> tuple[int, list[dict[str, Any]]]:
        """
        Recalculate scoring for all participants (or specific ones) against a weight table.

        Returns:
            Tuple of (count of successful calculations, list of errors)
        """
        from sqlalchemy import select
        from app.db.models import Participant

        if participant_ids:
            participants = participant_ids
        else:
            # Get all participants
            result = await self.db.execute(select(Participant.id))
            participants = [row[0] for row in result.fetchall()]

        success_count = 0
        errors: list[dict[str, Any]] = []

        for pid in participants:
            try:
                await self.calculate_score(pid, weight_table_id)
                success_count += 1
            except Exception as e:
                errors.append({
                    "participant_id": str(pid),
                    "error": str(e),
                })

        return success_count, errors

    def _serialize(
        self,
        scoring_result: ScoringResult,
    ) -> ScoringResultResponse:
        """Convert ORM entity to API schema."""
        weight_table = scoring_result.weight_table
        prof_activity = weight_table.prof_activity if weight_table else None

        penalties = []
        if scoring_result.penalties_applied:
            for p in scoring_result.penalties_applied:
                penalties.append(PenaltyApplied(
                    metric_code=p["metric_code"],
                    value=Decimal(p["value"]),
                    threshold=Decimal(p["threshold"]),
                    penalty=Decimal(p["penalty"]),
                ))

        metrics = []
        if scoring_result.metrics_used:
            for m in scoring_result.metrics_used:
                metrics.append(MetricUsed(
                    metric_code=m["metric_code"],
                    value=Decimal(m["value"]),
                    weight=Decimal(m["weight"]),
                    weighted_value=Decimal(m["weighted_value"]),
                ))

        return ScoringResultResponse(
            id=scoring_result.id,
            participant_id=scoring_result.participant_id,
            weight_table_id=scoring_result.weight_table_id,
            prof_activity_code=prof_activity.code if prof_activity else "unknown",
            prof_activity_name=prof_activity.name if prof_activity else "Unknown",
            base_score=Decimal(str(scoring_result.base_score)),
            penalty_multiplier=Decimal(str(scoring_result.penalty_multiplier)),
            final_score=Decimal(str(scoring_result.final_score)),
            penalties_applied=penalties,
            metrics_used=metrics,
            computed_at=scoring_result.computed_at,
        )

    async def get_participant_scores_response(
        self,
        participant_id: UUID,
        participant_name: str,
    ) -> ScoringResultListResponse:
        """Get serialized scoring results for a participant."""
        results = await self.get_participant_scores(participant_id)
        return ScoringResultListResponse(
            participant_id=participant_id,
            participant_name=participant_name,
            results=[self._serialize(r) for r in results],
        )
