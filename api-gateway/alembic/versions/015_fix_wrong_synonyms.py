"""Fix wrong synonyms assigned to incorrect metrics.

Revision ID: 015_fix_wrong_synonyms
Revises: 014_embedding_3072_dims
Create Date: 2026-02-06

Removes incorrectly assigned synonyms:
1. "Управленческий опыт" from potentsial_k_rukovodstvu metric
   (this synonym describes a different concept than leadership potential)
2. "Ориентация на безопасность" from zdorove metric
   (safety orientation is not the same as health)

Also cleans up:
- Stale embeddings that included the removed synonyms in indexed_text
- REJECTED metric_def for 'upravlencheskiy_opyt' (if exists)
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "015_fix_wrong_synonyms"
down_revision = "014_embedding_3072_dims"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # C3: Delete stale embeddings for REJECTED 'upravlencheskiy_opyt' metric
    op.execute(
        """
        DELETE FROM metric_embedding
        WHERE metric_def_id IN (
            SELECT id FROM metric_def
            WHERE code = 'upravlencheskiy_opyt'
              AND moderation_status = 'REJECTED'
        )
        """
    )

    # C3: Delete REJECTED metric_def 'upravlencheskiy_opyt'
    op.execute(
        """
        DELETE FROM metric_def
        WHERE code = 'upravlencheskiy_opyt'
          AND moderation_status = 'REJECTED'
        """
    )

    # Delete "Управленческий опыт" synonym from potentsial_k_rukovodstvu
    op.execute(
        """
        DELETE FROM metric_synonym
        WHERE synonym = 'Управленческий опыт'
          AND metric_def_id = (
              SELECT id FROM metric_def WHERE code = 'potentsial_k_rukovodstvu'
          )
        """
    )

    # Delete "Ориентация на безопасность" synonym from zdorove (if exists)
    op.execute(
        """
        DELETE FROM metric_synonym
        WHERE synonym = 'Ориентация на безопасность'
          AND metric_def_id = (
              SELECT id FROM metric_def WHERE code = 'zdorove'
          )
        """
    )

    # I1: Delete stale embeddings that included the removed synonyms in indexed_text
    # The embedding for potentsial_k_rukovodstvu included "Управленческий опыт"
    op.execute(
        """
        DELETE FROM metric_embedding
        WHERE indexed_text LIKE '%Управленческий опыт%'
          AND metric_def_id = (
              SELECT id FROM metric_def WHERE code = 'potentsial_k_rukovodstvu'
          )
        """
    )

    # The embedding for zdorove included "Ориентация на безопасность"
    op.execute(
        """
        DELETE FROM metric_embedding
        WHERE indexed_text LIKE '%Ориентация на безопасность%'
          AND metric_def_id = (
              SELECT id FROM metric_def WHERE code = 'zdorove'
          )
        """
    )


def downgrade() -> None:
    # Re-insert "Управленческий опыт" synonym for potentsial_k_rukovodstvu
    op.execute(
        """
        INSERT INTO metric_synonym (metric_def_id, synonym)
        SELECT id, 'Управленческий опыт'
        FROM metric_def
        WHERE code = 'potentsial_k_rukovodstvu'
        ON CONFLICT (synonym) DO NOTHING
        """
    )

    # Re-insert "Ориентация на безопасность" synonym for zdorove
    op.execute(
        """
        INSERT INTO metric_synonym (metric_def_id, synonym)
        SELECT id, 'Ориентация на безопасность'
        FROM metric_def
        WHERE code = 'zdorove'
        ON CONFLICT (synonym) DO NOTHING
        """
    )

    # Re-insert REJECTED metric_def 'upravlencheskiy_opyt' (best-effort)
    op.execute(
        """
        INSERT INTO metric_def (code, name, name_ru, moderation_status, min_value, max_value, sort_order)
        VALUES ('upravlencheskiy_opyt', 'Управленческий опыт', 'Управленческий опыт', 'REJECTED', 1, 10, 0)
        ON CONFLICT (code) DO NOTHING
        """
    )
