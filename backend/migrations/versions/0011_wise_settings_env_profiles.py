"""wise settings env profiles

Revision ID: 0011_wise_settings_env_profiles
Revises: 0010_wise_settings
Create Date: 2026-01-14 23:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_wise_settings_env_profiles"
down_revision = "0010_wise_settings"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("uq_wise_settings_company", "wise_settings", type_="unique")
    op.create_unique_constraint(
        "uq_wise_settings_company_env",
        "wise_settings",
        ["company_id", "wise_environment"],
    )
    op.add_column("wise_webhook_subscriptions", sa.Column("wise_environment", sa.String(), nullable=True))
    op.execute("UPDATE wise_webhook_subscriptions SET wise_environment = 'sandbox' WHERE wise_environment IS NULL")
    op.alter_column("wise_webhook_subscriptions", "wise_environment", nullable=False, server_default="sandbox")


def downgrade():
    op.drop_column("wise_webhook_subscriptions", "wise_environment")
    op.drop_constraint("uq_wise_settings_company_env", "wise_settings", type_="unique")
    op.create_unique_constraint("uq_wise_settings_company", "wise_settings", ["company_id"])
