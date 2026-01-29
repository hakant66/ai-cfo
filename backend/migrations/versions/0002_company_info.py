"""add company contact fields

Revision ID: 0002_company_info
Revises: 0001_initial
Create Date: 2026-01-13 21:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_company_info"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("companies", sa.Column("website", sa.String(), nullable=True))
    op.add_column("companies", sa.Column("contact_email", sa.String(), nullable=True))
    op.add_column("companies", sa.Column("contact_phone", sa.String(), nullable=True))


def downgrade():
    op.drop_column("companies", "contact_phone")
    op.drop_column("companies", "contact_email")
    op.drop_column("companies", "website")
