"""Upgrade metric_embedding to 3072 dimensions for text-embedding-3-large.

Revision ID: 014_embedding_3072_dims
Revises: 013_add_scoring_result_with_penalties
Create Date: 2026-02-05

Migrates from text-embedding-3-small (1536 dimensions) to text-embedding-3-large (3072 dimensions).

IMPORTANT: pgvector HNSW index has a 2000-dimension limit for standard vector type.
For 3072 dimensions, we use halfvec (half-precision) for the index which supports up to 4000 dims.
The storage column remains vector(3072) for full precision, but the index uses halfvec cast.

This migration:
1. Drops the existing HNSW index
2. Alters the vector column from vector(1536) to vector(3072)
3. Truncates existing embeddings (they must be regenerated with new model)
4. Creates HNSW index using halfvec cast for 3072 dimensions (HNSW limit is 2000 for vector, 4000 for halfvec)

After migration, run full reindex:
    POST /api/admin/metrics/reindex
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "014_embedding_3072_dims"
down_revision = "013_add_scoring_result_penalties"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing HNSW index (cannot alter vector dimensions with index)
    op.execute("DROP INDEX IF EXISTS idx_metric_embedding_vector")

    # Truncate existing embeddings - they are incompatible with new dimensions
    # and must be regenerated with the new model
    op.execute("TRUNCATE TABLE metric_embedding")

    # Alter vector column from 1536 to 3072 dimensions
    op.execute(
        """
        ALTER TABLE metric_embedding
        ALTER COLUMN embedding TYPE vector(3072)
        """
    )

    # Create HNSW index using halfvec cast for 3072 dimensions
    # Standard HNSW has 2000 dimension limit for vector, but 4000 for halfvec
    # This allows indexing 3072-dim vectors with minimal precision loss
    # halfvec_cosine_ops is the operator class for half-precision cosine distance
    op.execute(
        """
        CREATE INDEX idx_metric_embedding_vector
        ON metric_embedding USING hnsw ((embedding::halfvec(3072)) halfvec_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    # Drop HNSW index
    op.execute("DROP INDEX IF EXISTS idx_metric_embedding_vector")

    # Truncate embeddings - incompatible dimensions
    op.execute("TRUNCATE TABLE metric_embedding")

    # Revert to 1536 dimensions
    op.execute(
        """
        ALTER TABLE metric_embedding
        ALTER COLUMN embedding TYPE vector(1536)
        """
    )

    # Recreate HNSW index for original dimension (1536 is within 2000 limit)
    op.execute(
        """
        CREATE INDEX idx_metric_embedding_vector
        ON metric_embedding USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )
