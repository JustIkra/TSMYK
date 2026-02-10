"""Add organizations and departments.

Revision ID: 016_add_organizations
Revises: 015_fix_wrong_synonyms
Create Date: 2026-02-10

Creates organization and department tables.
Adds department_id FK to participant table.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP

revision = "016_add_organizations"
down_revision = "015_fix_wrong_synonyms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_organization_name", "organization", ["name"])

    op.create_table(
        "department",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organization.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "name", name="uq_department_org_name"),
    )
    op.create_index("ix_department_organization_id", "department", ["organization_id"])

    op.add_column(
        "participant",
        sa.Column(
            "department_id",
            UUID(as_uuid=True),
            sa.ForeignKey("department.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_participant_department_id", "participant", ["department_id"])


def downgrade() -> None:
    op.drop_index("ix_participant_department_id", table_name="participant")
    op.drop_column("participant", "department_id")
    op.drop_index("ix_department_organization_id", table_name="department")
    op.drop_table("department")
    op.drop_index("ix_organization_name", table_name="organization")
    op.drop_table("organization")
