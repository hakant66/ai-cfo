"""add manual override flag to exchange rates

Revision ID: 0007_exchange_rates_manual_override
Revises: 0006_exchange_rates
Create Date: 2026-01-14 17:10:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_exchange_rates_manual_override"
down_revision = "0006_exchange_rates"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("exchange_rates", sa.Column("manual_override", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.alter_column("exchange_rates", "manual_override", server_default=None)


def downgrade():
    op.drop_column("exchange_rates", "manual_override")
