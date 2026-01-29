"""add document embedding settings and expand embedding dimension

Revision ID: 0017_document_embedding_settings
Revises: 0016_stripe_metrics
Create Date: 2026-01-20 15:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0017_document_embedding_settings"
down_revision = "0016_stripe_metrics"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("documents", sa.Column("embedding_model", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("chunk_size", sa.Integer(), nullable=True))
    op.execute("DELETE FROM document_chunks")
    op.execute("UPDATE documents SET indexed_chunks = 0, indexed_at = NULL, status = 'queued'")
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(3072)")


def downgrade():
    op.execute("DELETE FROM document_chunks")
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1536)")
    op.execute("UPDATE documents SET indexed_chunks = 0, indexed_at = NULL, status = 'queued'")
    op.drop_column("documents", "chunk_size")
    op.drop_column("documents", "embedding_model")
