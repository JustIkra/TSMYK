"""Add scoring_result table with penalty support.

Revision ID: 013
Revises: 012
Create Date: 2026-02-04

New scoring system with:
- base_score: weighted average of metrics
- penalty_multiplier: product of (1 - penalty_i) for critical metrics below threshold
- final_score: base_score * penalty_multiplier
- penalties_applied: JSONB array of applied penalties

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP

# revision identifiers, used by Alembic.
revision = "013_add_scoring_result_penalties"
down_revision = "012_drop_scoring_result"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create scoring_result table with new structure
    op.create_table(
        "scoring_result",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("participant_id", UUID(as_uuid=True), sa.ForeignKey("participant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("weight_table_id", UUID(as_uuid=True), sa.ForeignKey("weight_table.id", ondelete="CASCADE"), nullable=False),
        sa.Column("base_score", sa.Numeric(5, 2), nullable=False, comment="Weighted average before penalties (0-10)"),
        sa.Column("penalty_multiplier", sa.Numeric(5, 4), nullable=False, server_default="1.0", comment="Product of (1-penalty) for failed critical metrics"),
        sa.Column("final_score", sa.Numeric(5, 2), nullable=False, comment="base_score * penalty_multiplier (0-10)"),
        sa.Column("penalties_applied", JSONB, nullable=True, comment="Array of {metric_code, value, threshold, penalty}"),
        sa.Column("metrics_used", JSONB, nullable=True, comment="Array of {metric_code, value, weight} used in calculation"),
        sa.Column("computed_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        # Constraints
        sa.CheckConstraint("base_score >= 0 AND base_score <= 10", name="scoring_result_base_score_check"),
        sa.CheckConstraint("penalty_multiplier >= 0 AND penalty_multiplier <= 1", name="scoring_result_penalty_multiplier_check"),
        sa.CheckConstraint("final_score >= 0 AND final_score <= 10", name="scoring_result_final_score_check"),
        sa.UniqueConstraint("participant_id", "weight_table_id", name="uq_scoring_result_participant_weight_table"),
    )

    # Create indexes
    op.create_index("ix_scoring_result_participant_id", "scoring_result", ["participant_id"])
    op.create_index("ix_scoring_result_weight_table_id", "scoring_result", ["weight_table_id"])
    op.create_index("ix_scoring_result_computed_at", "scoring_result", ["computed_at"])
    op.create_index("ix_scoring_result_final_score", "scoring_result", ["final_score"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_scoring_result_final_score", table_name="scoring_result")
    op.drop_index("ix_scoring_result_computed_at", table_name="scoring_result")
    op.drop_index("ix_scoring_result_weight_table_id", table_name="scoring_result")
    op.drop_index("ix_scoring_result_participant_id", table_name="scoring_result")

    # Drop table
    op.drop_table("scoring_result")
