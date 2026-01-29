"""add exchange rates table

Revision ID: 0006_exchange_rates
Revises: 0005_sales_quality_fields
Create Date: 2026-01-14 13:05:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_exchange_rates"
down_revision = "0005_sales_quality_fields"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pair", sa.String(), nullable=False, unique=True),
        sa.Column("rate", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("exchange_rates")
