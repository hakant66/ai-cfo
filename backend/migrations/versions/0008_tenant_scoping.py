"""add company scoping columns and constraints

Revision ID: 0008_tenant_scoping
Revises: 0007_exchange_rates_manual_override
Create Date: 2026-01-15 09:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_tenant_scoping"
down_revision = "0007_exchange_rates_manual_override"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("products", sa.Column("company_id", sa.Integer(), nullable=True))
    op.add_column("inventory_snapshots", sa.Column("company_id", sa.Integer(), nullable=True))
    op.add_column("order_lines", sa.Column("company_id", sa.Integer(), nullable=True))
    op.add_column("refunds", sa.Column("company_id", sa.Integer(), nullable=True))
    op.add_column("suppliers", sa.Column("company_id", sa.Integer(), nullable=True))
    op.add_column("purchase_order_lines", sa.Column("company_id", sa.Integer(), nullable=True))
    op.add_column("bank_transactions", sa.Column("company_id", sa.Integer(), nullable=True))
    op.add_column("exchange_rates", sa.Column("company_id", sa.Integer(), nullable=True))
    op.add_column("document_chunks", sa.Column("company_id", sa.Integer(), nullable=True))

    op.execute("UPDATE order_lines SET company_id = orders.company_id FROM orders WHERE order_lines.order_id = orders.id")
    op.execute("UPDATE refunds SET company_id = orders.company_id FROM orders WHERE refunds.order_id = orders.id")
    op.execute("UPDATE purchase_order_lines SET company_id = purchase_orders.company_id FROM purchase_orders WHERE purchase_order_lines.purchase_order_id = purchase_orders.id")
    op.execute("UPDATE bank_transactions SET company_id = bank_accounts.company_id FROM bank_accounts WHERE bank_transactions.bank_account_id = bank_accounts.id")
    op.execute("UPDATE document_chunks SET company_id = documents.company_id FROM documents WHERE document_chunks.document_id = documents.id")

    op.execute("UPDATE suppliers SET company_id = purchase_orders.company_id FROM purchase_orders WHERE suppliers.id = purchase_orders.supplier_id AND suppliers.company_id IS NULL")

    op.execute("""
        UPDATE products
        SET company_id = (SELECT id FROM companies ORDER BY id LIMIT 1)
        WHERE company_id IS NULL
    """)
    op.execute("""
        UPDATE inventory_snapshots
        SET company_id = (SELECT id FROM companies ORDER BY id LIMIT 1)
        WHERE company_id IS NULL
    """)
    op.execute("""
        UPDATE suppliers
        SET company_id = (SELECT id FROM companies ORDER BY id LIMIT 1)
        WHERE company_id IS NULL
    """)
    op.execute("""
        UPDATE exchange_rates
        SET company_id = (SELECT id FROM companies ORDER BY id LIMIT 1)
        WHERE company_id IS NULL
    """)

    op.alter_column("products", "company_id", nullable=False)
    op.alter_column("inventory_snapshots", "company_id", nullable=False)
    op.alter_column("order_lines", "company_id", nullable=False)
    op.alter_column("refunds", "company_id", nullable=False)
    op.alter_column("suppliers", "company_id", nullable=False)
    op.alter_column("purchase_order_lines", "company_id", nullable=False)
    op.alter_column("bank_transactions", "company_id", nullable=False)
    op.alter_column("exchange_rates", "company_id", nullable=False)
    op.alter_column("document_chunks", "company_id", nullable=False)

    op.drop_index("ix_orders_external_id", table_name="orders")
    op.drop_index("ix_products_sku", table_name="products")
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS products_sku_key")

    op.create_unique_constraint("uq_orders_company_external_id", "orders", ["company_id", "external_id"])
    op.create_unique_constraint("uq_products_company_sku", "products", ["company_id", "sku"])
    op.create_unique_constraint("uq_exchange_rates_company_pair", "exchange_rates", ["company_id", "pair"])


def downgrade():
    op.drop_constraint("uq_exchange_rates_company_pair", "exchange_rates", type_="unique")
    op.drop_constraint("uq_products_company_sku", "products", type_="unique")
    op.drop_constraint("uq_orders_company_external_id", "orders", type_="unique")

    op.create_index("ix_orders_external_id", "orders", ["external_id"], unique=True)
    op.create_index("ix_products_sku", "products", ["sku"], unique=True)

    op.drop_column("document_chunks", "company_id")
    op.drop_column("exchange_rates", "company_id")
    op.drop_column("bank_transactions", "company_id")
    op.drop_column("purchase_order_lines", "company_id")
    op.drop_column("suppliers", "company_id")
    op.drop_column("refunds", "company_id")
    op.drop_column("order_lines", "company_id")
    op.drop_column("inventory_snapshots", "company_id")
    op.drop_column("products", "company_id")
