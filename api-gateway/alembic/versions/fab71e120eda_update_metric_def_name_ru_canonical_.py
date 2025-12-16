"""update_metric_def_name_ru_canonical_values

Revision ID: fab71e120eda
Revises: 2ede3ff233bb
Create Date: 2025-12-15 16:20:26.524891

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.services.metric_localization import METRIC_DISPLAY_NAMES_RU


# revision identifiers, used by Alembic.
revision: str = 'fab71e120eda'
down_revision: Union[str, None] = '2ede3ff233bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update name_ru field with canonical Russian display names from metric_localization."""
    connection = op.get_bind()

    # Update each metric with canonical Russian name
    update_stmt = sa.text(
        "UPDATE metric_def SET name_ru = :name_ru WHERE code = :code"
    )

    for code, name_ru in METRIC_DISPLAY_NAMES_RU.items():
        connection.execute(update_stmt, {"code": code, "name_ru": name_ru})


def downgrade() -> None:
    """No rollback needed - canonical names are data corrections, not schema changes."""
    pass
