"""
Pydantic schemas for scoring calculations.

Defines request/response schemas for participant scoring based on weight tables.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PenaltyApplied(BaseModel):
    """Details of a penalty applied during scoring."""

    metric_code: str = Field(..., description="Metric code that triggered the penalty")
    value: Decimal = Field(..., description="Participant's actual value for the metric")
    threshold: Decimal = Field(..., description="Threshold below which penalty applies")
    penalty: Decimal = Field(..., description="Penalty value that was applied")


class MetricUsed(BaseModel):
    """Details of a metric used in score calculation."""

    metric_code: str = Field(..., description="Metric code")
    value: Decimal = Field(..., description="Participant's value")
    weight: Decimal = Field(..., description="Weight applied to this metric")
    weighted_value: Decimal = Field(..., description="value * weight")


class ScoringResultResponse(BaseModel):
    """Scoring result for a participant against a weight table."""

    id: UUID
    participant_id: UUID
    weight_table_id: UUID
    prof_activity_code: str = Field(..., description="Professional activity code")
    prof_activity_name: str = Field(..., description="Professional activity name")
    base_score: Decimal = Field(..., description="Weighted average before penalties (0-10)")
    penalty_multiplier: Decimal = Field(..., description="Product of (1-penalty) factors")
    final_score: Decimal = Field(..., description="base_score * penalty_multiplier")
    penalties_applied: list[PenaltyApplied] = Field(
        default_factory=list,
        description="List of penalties applied",
    )
    metrics_used: list[MetricUsed] = Field(
        default_factory=list,
        description="List of metrics used in calculation",
    )
    computed_at: datetime

    model_config = {"from_attributes": True}


class ScoringResultListResponse(BaseModel):
    """List of scoring results for a participant."""

    participant_id: UUID
    participant_name: str
    results: list[ScoringResultResponse]


class RecalculateRequest(BaseModel):
    """Request to recalculate scoring for a participant."""

    weight_table_ids: list[UUID] | None = Field(
        None,
        description="Specific weight tables to recalculate. If None, recalculates all.",
    )


class BatchRecalculateRequest(BaseModel):
    """Request to batch recalculate scoring."""

    participant_ids: list[UUID] | None = Field(
        None,
        description="Specific participants. If None, recalculates all.",
    )
    weight_table_ids: list[UUID] | None = Field(
        None,
        description="Specific weight tables. If None, uses all.",
    )


class BatchRecalculateResponse(BaseModel):
    """Response from batch recalculation."""

    total_calculated: int = Field(..., description="Number of scoring results calculated")
    errors: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of errors encountered",
    )
