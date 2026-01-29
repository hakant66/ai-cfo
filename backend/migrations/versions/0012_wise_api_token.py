"""add wise api token

Revision ID: 0012_wise_api_token
Revises: 0011_wise_settings_env_profiles
Create Date: 2026-01-15 00:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_wise_api_token"
down_revision = "0011_wise_settings_env_profiles"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("wise_settings", sa.Column("wise_api_token_encrypted", sa.String(), nullable=True))


def downgrade():
    op.drop_column("wise_settings", "wise_api_token_encrypted")
