"""Drop scoring_result table (legacy).

Revision ID: 012
Revises: 011
Create Date: 2026-02-03

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "012_drop_scoring_result"
down_revision = "011_add_canonical_metric_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop indexes first
    op.drop_index("ix_scoring_result_participant_computed", table_name="scoring_result")
    op.drop_index("ix_scoring_result_computed_at", table_name="scoring_result")
    op.drop_index("ix_scoring_result_participant_id", table_name="scoring_result")

    # Drop table
    op.drop_table("scoring_result")


def downgrade() -> None:
    # Recreate table (for rollback)
    op.execute("""
        CREATE TABLE scoring_result (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            participant_id UUID NOT NULL REFERENCES participant(id) ON DELETE CASCADE,
            weight_table_id UUID NOT NULL REFERENCES weight_table(id) ON DELETE RESTRICT,
            score_pct NUMERIC(5, 2) NOT NULL CHECK (score_pct >= 0 AND score_pct <= 100),
            strengths JSONB,
            dev_areas JSONB,
            computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            compute_notes TEXT
        )
    """)

    # Recreate indexes
    op.create_index("ix_scoring_result_participant_id", "scoring_result", ["participant_id"])
    op.create_index("ix_scoring_result_computed_at", "scoring_result", ["computed_at"])
    op.create_index(
        "ix_scoring_result_participant_computed",
        "scoring_result",
        ["participant_id", "computed_at"],
    )
