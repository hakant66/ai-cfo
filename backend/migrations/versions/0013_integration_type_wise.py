"""add wise integration type

Revision ID: 0013_integration_type_wise
Revises: 0012_wise_api_token
Create Date: 2026-01-15 00:25:00.000000
"""

from alembic import op


revision = "0013_integration_type_wise"
down_revision = "0012_wise_api_token"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE integrationtype ADD VALUE IF NOT EXISTS 'Wise'")


def downgrade():
    # Enum value removal is not supported in Postgres without recreation.
    pass
