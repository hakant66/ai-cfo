"""add wise integration tables

Revision ID: 0009_wise_integration
Revises: 0008_tenant_scoping
Create Date: 2026-01-14 23:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_wise_integration"
down_revision = "0008_tenant_scoping"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("bank_accounts", sa.Column("provider", sa.String(), nullable=True))
    op.add_column("bank_accounts", sa.Column("provider_account_id", sa.String(), nullable=True))
    op.create_unique_constraint(
        "uq_bank_accounts_company_provider",
        "bank_accounts",
        ["company_id", "provider", "provider_account_id"],
    )

    op.add_column("bank_transactions", sa.Column("currency", sa.String(), nullable=True))
    op.add_column("bank_transactions", sa.Column("provider", sa.String(), nullable=True))
    op.add_column("bank_transactions", sa.Column("provider_transaction_id", sa.String(), nullable=True))
    op.add_column("bank_transactions", sa.Column("raw_reference", sa.String(), nullable=True))
    op.create_unique_constraint(
        "uq_bank_transactions_company_provider",
        "bank_transactions",
        ["company_id", "provider", "provider_transaction_id"],
    )

    op.create_table(
        "bank_balances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("bank_account_id", sa.Integer(), sa.ForeignKey("bank_accounts.id"), nullable=False),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("provider_account_id", sa.String(), nullable=True),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("balance", sa.Float(), nullable=False, server_default="0"),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_bank_balances_company_account_time",
        "bank_balances",
        ["company_id", "bank_account_id", "captured_at"],
    )

    op.create_table(
        "integration_credentials_wise",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("integration_id", sa.Integer(), sa.ForeignKey("integrations.id"), nullable=False),
        sa.Column("wise_environment", sa.String(), nullable=False),
        sa.Column("oauth_access_token_encrypted", sa.String(), nullable=False),
        sa.Column("oauth_refresh_token_encrypted", sa.String(), nullable=False),
        sa.Column("token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("scopes", sa.JSON(), nullable=True),
        sa.Column("wise_profile_id", sa.String(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("sync_cursor_transactions", sa.JSON(), nullable=True),
        sa.Column("key_version", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_unique_constraint(
        "uq_wise_credentials_company_env",
        "integration_credentials_wise",
        ["company_id", "wise_environment"],
    )

    op.create_table(
        "wise_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("wise_profile_id", sa.String(), nullable=False),
        sa.Column("profile_type", sa.String(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
    )
    op.create_unique_constraint(
        "uq_wise_profiles_company",
        "wise_profiles",
        ["company_id", "wise_profile_id"],
    )

    op.create_table(
        "wise_balance_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("wise_balance_account_id", sa.String(), nullable=False),
        sa.Column("wise_profile_id", sa.String(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
    )
    op.create_unique_constraint(
        "uq_wise_balance_accounts_company",
        "wise_balance_accounts",
        ["company_id", "wise_balance_account_id"],
    )

    op.create_table(
        "wise_balances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("wise_balance_account_id", sa.String(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_wise_balances_company_account_time",
        "wise_balances",
        ["company_id", "wise_balance_account_id", "timestamp"],
    )

    op.create_table(
        "wise_transactions_raw",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("wise_transaction_id", sa.String(), nullable=False),
        sa.Column("wise_balance_account_id", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
    )
    op.create_unique_constraint(
        "uq_wise_transactions_company",
        "wise_transactions_raw",
        ["company_id", "wise_transaction_id"],
    )

    op.create_table(
        "wise_webhook_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("wise_subscription_id", sa.String(), nullable=False),
        sa.Column("event_types", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("secret_ref", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_unique_constraint(
        "uq_wise_webhook_company",
        "wise_webhook_subscriptions",
        ["company_id", "wise_subscription_id"],
    )

    op.create_table(
        "wise_webhook_receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("wise_subscription_id", sa.String(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=True),
    )

    op.create_table(
        "wise_transfers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approvals", sa.JSON(), nullable=True),
        sa.Column("wise_transfer_id", sa.String(), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_unique_constraint(
        "uq_wise_transfers_company_idempotency",
        "wise_transfers",
        ["company_id", "idempotency_key"],
    )

    op.create_table(
        "wise_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approvals", sa.JSON(), nullable=True),
        sa.Column("wise_batch_id", sa.String(), nullable=True),
        sa.Column("raw", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_unique_constraint(
        "uq_wise_batches_company_idempotency",
        "wise_batches",
        ["company_id", "idempotency_key"],
    )

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "sync_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("environment", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("counts", sa.JSON(), nullable=True),
        sa.Column("error_summary", sa.String(), nullable=True),
        sa.Column("trace_id", sa.String(), nullable=True),
    )


def downgrade():
    op.drop_table("sync_runs")
    op.drop_table("audit_log")
    op.drop_constraint("uq_wise_batches_company_idempotency", "wise_batches", type_="unique")
    op.drop_table("wise_batches")
    op.drop_constraint("uq_wise_transfers_company_idempotency", "wise_transfers", type_="unique")
    op.drop_table("wise_transfers")
    op.drop_table("wise_webhook_receipts")
    op.drop_constraint("uq_wise_webhook_company", "wise_webhook_subscriptions", type_="unique")
    op.drop_table("wise_webhook_subscriptions")
    op.drop_constraint("uq_wise_transactions_company", "wise_transactions_raw", type_="unique")
    op.drop_table("wise_transactions_raw")
    op.drop_index("ix_wise_balances_company_account_time", table_name="wise_balances")
    op.drop_table("wise_balances")
    op.drop_constraint("uq_wise_balance_accounts_company", "wise_balance_accounts", type_="unique")
    op.drop_table("wise_balance_accounts")
    op.drop_constraint("uq_wise_profiles_company", "wise_profiles", type_="unique")
    op.drop_table("wise_profiles")
    op.drop_constraint("uq_wise_credentials_company_env", "integration_credentials_wise", type_="unique")
    op.drop_table("integration_credentials_wise")
    op.drop_index("ix_bank_balances_company_account_time", table_name="bank_balances")
    op.drop_table("bank_balances")
    op.drop_constraint("uq_bank_transactions_company_provider", "bank_transactions", type_="unique")
    op.drop_column("bank_transactions", "raw_reference")
    op.drop_column("bank_transactions", "provider_transaction_id")
    op.drop_column("bank_transactions", "provider")
    op.drop_column("bank_transactions", "currency")
    op.drop_constraint("uq_bank_accounts_company_provider", "bank_accounts", type_="unique")
    op.drop_column("bank_accounts", "provider_account_id")
    op.drop_column("bank_accounts", "provider")
