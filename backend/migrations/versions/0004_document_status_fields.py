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
    pass


def downgrade():
    pass
