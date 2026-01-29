"""add stripe integration type

Revision ID: 0015_integration_type_stripe
Revises: 0014_drop_exchange_rates_pair_unique
Create Date: 2026-01-18 21:30:00.000000
"""

from alembic import op

revision = "0015_integration_type_stripe"
down_revision = "0014_drop_exchange_rates_pair_unique"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE integrationtype ADD VALUE IF NOT EXISTS 'Stripe'")


def downgrade():
    # Enum value removal is not supported in Postgres without recreation.
    pass
