"""drop legacy unique constraint on exchange_rates.pair

Revision ID: 0014_drop_exchange_rates_pair_unique
Revises: 0013_integration_type_wise
Create Date: 2026-01-18 20:45:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0014_drop_exchange_rates_pair_unique"
down_revision = "0013_integration_type_wise"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE exchange_rates DROP CONSTRAINT IF EXISTS exchange_rates_pair_key")
        exists = bind.execute(
            sa.text("SELECT 1 FROM pg_constraint WHERE conname = 'uq_exchange_rates_company_pair'")
        ).scalar()
        if not exists:
            op.create_unique_constraint("uq_exchange_rates_company_pair", "exchange_rates", ["company_id", "pair"])


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE exchange_rates DROP CONSTRAINT IF EXISTS uq_exchange_rates_company_pair")
        op.create_unique_constraint("exchange_rates_pair_key", "exchange_rates", ["pair"])
