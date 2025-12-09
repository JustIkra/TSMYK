"""add full_name to user

Revision ID: a1b2c3d4e5f6
Revises: 6c5cde8c9886
Create Date: 2025-12-09 21:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "6c5cde8c9886"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("full_name", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user", "full_name")
