"""merge_heads

Revision ID: 6c5cde8c9886
Revises: d952812cd1d6, f8d4d2f6244a
Create Date: 2025-12-09 13:19:49.340378

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c5cde8c9886'
down_revision: Union[str, None] = ('d952812cd1d6', 'f8d4d2f6244a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
