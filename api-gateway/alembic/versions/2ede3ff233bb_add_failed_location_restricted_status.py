"""add_failed_location_restricted_status

Revision ID: 2ede3ff233bb
Revises: a1b2c3d4e5f6
Create Date: 2025-12-10 17:40:01.903256

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2ede3ff233bb'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
