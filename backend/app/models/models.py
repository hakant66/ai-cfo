from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON, Enum, Date
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from pgvector.sqlalchemy import Vector


class Role(enum.Enum):
    founder = "Founder"
    finance = "Finance"
    ops = "Ops"
    marketing = "Marketing"
    readonly = "ReadOnly"


class IntegrationType(enum.Enum):
    shopify = "Shopify"
    accounting = "Accounting"
    banking = "Banking"
    marketing = "Marketing"
    wise = "Wise"
    stripe = "Stripe"


class AlertSeverity(enum.Enum):
    low = "Low"
    medium = "Medium"
    high = "High"


class AlertType(enum.Enum):
    spend_spike = "SpendSpike"
    conversion_drop = "ConversionDrop"
    return_rate_jump = "ReturnRateJump"
    stockout_risk = "StockoutRisk"
    overstock_risk = "OverstockRisk"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    website = Column(String)
    contact_email = Column(String)
    contact_phone = Column(String)
    currency = Column(String, default="USD")
    timezone = Column(String, default="UTC")
    settlement_lag_days = Column(Integer, default=2)
    thresholds = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utcnow)

    users = relationship("User", back_populates="company")


def enum_values(enum_cls):
    return [member.value for member in enum_cls]


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(Role, values_callable=enum_values), nullable=False)
    is_active = Column(Boolean, default=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow)

    company = relationship("Company", back_populates="users")


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    type = Column(Enum(IntegrationType, values_callable=enum_values), nullable=False)
    status = Column(String, default="disconnected")
    credentials = Column(JSON, default=dict)
    last_sync_at = Column(DateTime)
    created_at = Column(DateTime, default=utcnow)


class StripeMetric(Base):
    __tablename__ = "stripe_metrics"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    metric_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class IntegrationCredentialWise(Base):
    __tablename__ = "integration_credentials_wise"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False)
    wise_environment = Column(String, nullable=False)
    oauth_access_token_encrypted = Column(String, nullable=False)
    oauth_refresh_token_encrypted = Column(String, nullable=False)
    token_expires_at = Column(DateTime)
    scopes = Column(JSON, default=list)
    wise_profile_id = Column(String)
    last_sync_at = Column(DateTime)
    sync_cursor_transactions = Column(JSON, default=dict)
    key_version = Column(String, default="v1")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow)


class WiseSettings(Base):
    __tablename__ = "wise_settings"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    wise_client_id = Column(String, nullable=True)
    wise_client_secret_encrypted = Column(String, nullable=True)
    wise_api_token_encrypted = Column(String, nullable=True)
    wise_environment = Column(String, nullable=False, default="sandbox")
    webhook_secret_encrypted = Column(String, nullable=True)
    key_version = Column(String, default="v1")
    updated_at = Column(DateTime, default=utcnow)


class WiseProfile(Base):
    __tablename__ = "wise_profiles"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    wise_profile_id = Column(String, nullable=False)
    profile_type = Column(String, nullable=False)
    details = Column(JSON, default=dict)
    fetched_at = Column(DateTime, default=utcnow)


class WiseBalanceAccount(Base):
    __tablename__ = "wise_balance_accounts"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    wise_balance_account_id = Column(String, nullable=False)
    wise_profile_id = Column(String, nullable=False)
    currency = Column(String, nullable=False)
    name = Column(String)
    status = Column(String)
    details = Column(JSON, default=dict)
    fetched_at = Column(DateTime, default=utcnow)


class WiseBalance(Base):
    __tablename__ = "wise_balances"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    wise_balance_account_id = Column(String, nullable=False)
    currency = Column(String, nullable=False)
    amount = Column(Float, default=0.0)
    timestamp = Column(DateTime, nullable=False)
    fetched_at = Column(DateTime, default=utcnow)


class WiseTransactionRaw(Base):
    __tablename__ = "wise_transactions_raw"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    wise_transaction_id = Column(String, nullable=False)
    wise_balance_account_id = Column(String, nullable=False)
    occurred_at = Column(DateTime, nullable=False)
    amount = Column(Float, default=0.0)
    currency = Column(String, nullable=False)
    description = Column(String)
    raw = Column(JSON, default=dict)
    fetched_at = Column(DateTime, default=utcnow)


class WiseWebhookSubscription(Base):
    __tablename__ = "wise_webhook_subscriptions"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    wise_subscription_id = Column(String, nullable=False)
    wise_environment = Column(String, nullable=False, default="sandbox")
    event_types = Column(JSON, default=list)
    status = Column(String, default="active")
    secret_ref = Column(String)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow)


class WiseWebhookReceipt(Base):
    __tablename__ = "wise_webhook_receipts"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    wise_subscription_id = Column(String)
    event_type = Column(String)
    status = Column(String, default="received")
    received_at = Column(DateTime, default=utcnow)
    reason = Column(String)
    raw = Column(JSON, default=dict)


class WiseTransfer(Base):
    __tablename__ = "wise_transfers"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    status = Column(String, default="created")
    reference = Column(String)
    idempotency_key = Column(String, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    approvals = Column(JSON, default=list)
    wise_transfer_id = Column(String)
    raw = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow)


class WiseBatch(Base):
    __tablename__ = "wise_batches"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    status = Column(String, default="created")
    reference = Column(String)
    idempotency_key = Column(String, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    approvals = Column(JSON, default=list)
    wise_batch_id = Column(String)
    raw = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String)
    metadata_json = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=utcnow)


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    provider = Column(String, nullable=False)
    environment = Column(String, nullable=False)
    status = Column(String, default="started")
    started_at = Column(DateTime, default=utcnow)
    ended_at = Column(DateTime)
    counts = Column(JSON, default=dict)
    error_summary = Column(String)
    trace_id = Column(String)


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    sku = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    product_type = Column(String)
    unit_cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=utcnow)


class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshots"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    sku = Column(String, index=True, nullable=False)
    on_hand = Column(Integer, default=0)
    snapshot_date = Column(Date, nullable=False)
    source = Column(String, default="manual")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    external_id = Column(String, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    total_price = Column(Float, default=0.0)
    discounts = Column(Float, default=0.0)
    refunds = Column(Float, default=0.0)
    net_sales = Column(Float, default=0.0)
    created_at = Column(DateTime, nullable=False)
    source = Column(String, default="shopify")
    customer_id = Column(String)
    customer_email_hash = Column(String)
    shipping_country = Column(String)
    shipping_region = Column(String)
    currency_code = Column(String)
    sales_channel = Column(String)
    source_name = Column(String)
    app_id = Column(String)
    referring_site = Column(String)
    landing_site = Column(String)
    order_tags = Column(String)


class OrderLine(Base):
    __tablename__ = "order_lines"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    sku = Column(String, nullable=False)
    quantity = Column(Integer, default=0)
    unit_price = Column(Float, default=0.0)
    product_name = Column(String)
    product_type = Column(String)


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    amount = Column(Float, default=0.0)
    created_at = Column(DateTime, nullable=False)


class Payout(Base):
    __tablename__ = "payouts"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    external_id = Column(String)
    amount = Column(Float, default=0.0)
    payout_date = Column(Date, nullable=False)
    source = Column(String, default="shopify")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String)
    created_at = Column(DateTime, default=utcnow)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    status = Column(String, default="open")
    created_at = Column(DateTime, default=utcnow)
    promised_date = Column(Date)
    received_date = Column(Date)


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"

    id = Column(Integer, primary_key=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    sku = Column(String, nullable=False)
    quantity = Column(Integer, default=0)
    unit_cost = Column(Float, default=0.0)


class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    vendor = Column(String, nullable=False)
    amount = Column(Float, default=0.0)
    due_date = Column(Date, nullable=False)
    status = Column(String, default="open")
    criticality = Column(String, default="deferrable")
    created_at = Column(DateTime, default=utcnow)


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    currency = Column(String, default="USD")
    balance = Column(Float, default=0.0)
    provider = Column(String, default="manual")
    provider_account_id = Column(String)


class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id = Column(Integer, primary_key=True)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    posted_at = Column(Date, nullable=False)
    amount = Column(Float, default=0.0)
    currency = Column(String)
    description = Column(String)
    category = Column(String)
    provider = Column(String, default="manual")
    provider_transaction_id = Column(String)
    raw_reference = Column(String)


class BankBalance(Base):
    __tablename__ = "bank_balances"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=False)
    provider = Column(String, default="manual")
    provider_account_id = Column(String)
    currency = Column(String, nullable=False)
    balance = Column(Float, default=0.0)
    captured_at = Column(DateTime, nullable=False)


class MarketingSpend(Base):
    __tablename__ = "marketing_spend"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    source = Column(String, default="manual")
    spend_date = Column(Date, nullable=False)
    amount = Column(Float, default=0.0)


class MetricRun(Base):
    __tablename__ = "metric_runs"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    metric_name = Column(String, nullable=False)
    value = Column(JSON, nullable=False)
    currency = Column(String)
    time_window = Column(String)
    sources = Column(JSON, default=list)
    provenance = Column(String, nullable=False)
    last_refresh = Column(DateTime, default=utcnow)
    query_id = Column(String, nullable=False)


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    pair = Column(String, nullable=False)
    rate = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=utcnow, nullable=False)
    manual_override = Column(Boolean, default=False, nullable=False)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    alert_type = Column(Enum(AlertType, values_callable=enum_values), nullable=False)
    severity = Column(Enum(AlertSeverity, values_callable=enum_values), nullable=False)
    message = Column(String, nullable=False)
    metadata_json = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=utcnow)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    status = Column(String, default="queued")
    indexed_chunks = Column(Integer, default=0)
    indexed_at = Column(DateTime)
    error_message = Column(String)
    embedding_model = Column(String)
    chunk_size = Column(Integer)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=utcnow)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(String, nullable=False)
    embedding = Column(Vector(3072), nullable=False)
