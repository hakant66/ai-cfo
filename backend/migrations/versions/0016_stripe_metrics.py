"""add stripe metrics table

Revision ID: 0016_stripe_metrics
Revises: 0015_integration_type_stripe
Create Date: 2026-01-18 22:15:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0016_stripe_metrics"
down_revision = "0015_integration_type_stripe"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "stripe_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("metric_type", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_stripe_metrics_company_id", "stripe_metrics", ["company_id"])
    op.create_index("ix_stripe_metrics_metric_type", "stripe_metrics", ["metric_type"])


def downgrade():
    op.drop_index("ix_stripe_metrics_metric_type", table_name="stripe_metrics")
    op.drop_index("ix_stripe_metrics_company_id", table_name="stripe_metrics")
    op.drop_table("stripe_metrics")
