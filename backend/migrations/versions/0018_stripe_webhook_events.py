"""stripe webhook events idempotency log

Revision ID: 0018_stripe_webhook_events
Revises: 0017_document_embedding_settings
Create Date: 2026-05-20 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import true as sql_true

revision = "0018_stripe_webhook_events"
down_revision = "0017_document_embedding_settings"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "stripe_webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("stripe_event_id", sa.String(), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=True),
        sa.Column("livemode", sa.Boolean(), nullable=False, server_default=sql_true()),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_stripe_webhook_events_company_id", "stripe_webhook_events", ["company_id"])
    op.create_index("ix_stripe_webhook_events_event_type", "stripe_webhook_events", ["event_type"])
    op.create_index(
        "uq_stripe_webhook_events_stripe_event_id",
        "stripe_webhook_events",
        ["stripe_event_id"],
        unique=True,
    )


def downgrade():
    op.drop_index("uq_stripe_webhook_events_stripe_event_id", table_name="stripe_webhook_events")
    op.drop_index("ix_stripe_webhook_events_event_type", table_name="stripe_webhook_events")
    op.drop_index("ix_stripe_webhook_events_company_id", table_name="stripe_webhook_events")
    op.drop_table("stripe_webhook_events")
