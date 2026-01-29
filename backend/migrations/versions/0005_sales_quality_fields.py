"""add sales quality fields

Revision ID: 0005_sales_quality_fields
Revises: 0004_document_status_fields
Create Date: 2026-01-13 23:20:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_sales_quality_fields"
down_revision = "0004_document_status_fields"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products", sa.Column("product_type", sa.String(), nullable=True))
    op.add_column("orders", sa.Column("customer_id", sa.String(), nullable=True))
    op.add_column("orders", sa.Column("customer_email_hash", sa.String(), nullable=True))
    op.add_column("orders", sa.Column("shipping_country", sa.String(), nullable=True))
    op.add_column("orders", sa.Column("shipping_region", sa.String(), nullable=True))
    op.add_column("orders", sa.Column("currency_code", sa.String(), nullable=True))
    op.add_column("orders", sa.Column("sales_channel", sa.String(), nullable=True))
    op.add_column("orders", sa.Column("source_name", sa.String(), nullable=True))
    op.add_column("orders", sa.Column("app_id", sa.String(), nullable=True))
    op.add_column("orders", sa.Column("referring_site", sa.String(), nullable=True))
    op.add_column("orders", sa.Column("landing_site", sa.String(), nullable=True))
    op.add_column("orders", sa.Column("order_tags", sa.String(), nullable=True))
    op.add_column("order_lines", sa.Column("product_name", sa.String(), nullable=True))
    op.add_column("order_lines", sa.Column("product_type", sa.String(), nullable=True))


def downgrade():
    op.drop_column("order_lines", "product_type")
    op.drop_column("order_lines", "product_name")
    op.drop_column("orders", "order_tags")
    op.drop_column("orders", "landing_site")
    op.drop_column("orders", "referring_site")
    op.drop_column("orders", "app_id")
    op.drop_column("orders", "source_name")
    op.drop_column("orders", "sales_channel")
    op.drop_column("orders", "currency_code")
    op.drop_column("orders", "shipping_region")
    op.drop_column("orders", "shipping_country")
    op.drop_column("orders", "customer_email_hash")
    op.drop_column("orders", "customer_id")
    op.drop_column("products", "product_type")
