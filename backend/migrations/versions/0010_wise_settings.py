"""add wise settings table

Revision ID: 0010_wise_settings
Revises: 0009_wise_integration
Create Date: 2026-01-14 23:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_wise_settings"
down_revision = "0009_wise_integration"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "wise_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("wise_client_id", sa.String(), nullable=True),
        sa.Column("wise_client_secret_encrypted", sa.String(), nullable=True),
        sa.Column("wise_environment", sa.String(), nullable=False, server_default="sandbox"),
        sa.Column("webhook_secret_encrypted", sa.String(), nullable=True),
        sa.Column("key_version", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_unique_constraint("uq_wise_settings_company", "wise_settings", ["company_id"])


def downgrade():
    op.drop_constraint("uq_wise_settings_company", "wise_settings", type_="unique")
    op.drop_table("wise_settings")
