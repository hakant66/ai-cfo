"""add document status fields

Revision ID: 0004_document_status_fields
Revises: 0003_documents_semantic_search
Create Date: 2026-01-13 22:45:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_document_status_fields"
down_revision = "0003_documents_semantic_search"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("documents", sa.Column("status", sa.String(), nullable=False, server_default="queued"))
    op.add_column("documents", sa.Column("indexed_chunks", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("documents", sa.Column("indexed_at", sa.DateTime(), nullable=True))
    op.add_column("documents", sa.Column("error_message", sa.String(), nullable=True))


def downgrade():
    op.drop_column("documents", "error_message")
    op.drop_column("documents", "indexed_at")
    op.drop_column("documents", "indexed_chunks")
    op.drop_column("documents", "status")
