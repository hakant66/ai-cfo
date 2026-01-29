from celery import Celery
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.core.database import SessionLocal
import hashlib
from app.models.models import Company, Integration, IntegrationType, Order, OrderLine, Product, InventorySnapshot, Refund, Document, IntegrationCredentialWise
from app.integrations.shopify import fetch_orders, fetch_inventory
from app.services.alerts import recompute_alerts
from app.services.documents import ingest_document
from app.services.locks import try_advisory_lock, release_advisory_lock
from app.services.sync_runs import start_sync_run, finish_sync_run
from app.services.audit_log import log_event
from app.connectors.wise.connector import WiseConnector

celery = Celery("ai_cfo", broker=settings.redis_url, backend=settings.redis_url)


@celery.task
def sync_shopify_data(company_id: int):
    db: Session = SessionLocal()
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        shift_demo_orders = company is not None and company.name == "Demo Retail Co"
        integration = db.query(Integration).filter(
            Integration.company_id == company_id,
            Integration.type == IntegrationType.shopify,
        ).first()
        if not integration:
            return "no_shopify"
        creds = integration.credentials or {}
        shop_domain = creds.get("shop_domain")
        access_token = creds.get("access_token")
        if not shop_domain or not access_token:
            return "missing_credentials"
        orders = fetch_orders(shop_domain, access_token)
        def hash_email(email: str | None) -> str | None:
            if not email:
                return None
            return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()

        def infer_sales_channel(order_payload: dict) -> str:
            source_name = (order_payload.get("source_name") or "").lower()
            tags = (order_payload.get("tags") or "").lower()
            referring_site = (order_payload.get("referring_site") or "").lower()
            landing_site = (order_payload.get("landing_site") or "").lower()
            if "wholesale" in tags or "wholesale" in source_name:
                return "Wholesale"
            if "amazon" in tags or "amazon" in referring_site or "amazon" in landing_site:
                return "Marketplace-1"
            if "etsy" in tags or "etsy" in referring_site or "etsy" in landing_site:
                return "Marketplace-1"
            if source_name in {"web", "online_store", "shopify"}:
                return "DTC(Direct-to-Consumer)"
            return "Unknown"

        for order in orders:
            external_id_raw = str(order["id"])
            alt_external_id = f"{company_id}:{external_id_raw}"
            existing = db.query(Order).filter(
                Order.external_id.in_([external_id_raw, alt_external_id]),
                Order.company_id == company_id,
            ).first()
            external_id = external_id_raw
            if not existing:
                conflict = db.query(Order).filter(
                    Order.external_id == external_id_raw,
                    Order.company_id != company_id,
                ).first()
                if conflict:
                    external_id = alt_external_id
            total_price = float(order.get("total_price") or 0)
            discounts = float(order.get("total_discounts") or 0)
            refunds_total = sum(float(refund.get("amount") or 0) for refund in order.get("refunds", []))
            created_at_raw = order.get("created_at") or datetime.now(timezone.utc).isoformat()
            created_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
            if shift_demo_orders:
                created_at = created_at - timedelta(days=1)
            customer = order.get("customer") or {}
            shipping = order.get("shipping_address") or {}
            customer_id = customer.get("id")
            customer_email_hash = hash_email(order.get("email") or customer.get("email"))
            currency_code = order.get("currency") or order.get("currency_code")
            shipping_country = shipping.get("country_code") or shipping.get("country") or shipping.get("countryCode")
            shipping_region = shipping.get("province_code") or shipping.get("province") or shipping.get("provinceCode")
            sales_channel = infer_sales_channel(order)
            if existing:
                existing.total_price = total_price
                existing.discounts = discounts
                existing.refunds = refunds_total
                existing.net_sales = total_price - discounts - refunds_total
                if existing.created_at is None:
                    existing.created_at = created_at
                existing.customer_id = customer_id
                existing.customer_email_hash = customer_email_hash
                existing.shipping_country = shipping_country
                existing.shipping_region = shipping_region
                existing.currency_code = currency_code
                existing.sales_channel = sales_channel
                existing.source_name = order.get("source_name")
                existing.app_id = str(order.get("app_id") or "") or None
                existing.referring_site = order.get("referring_site")
                existing.landing_site = order.get("landing_site")
                existing.order_tags = order.get("tags")
                order_row = existing
            else:
                order_row = Order(
                    external_id=external_id,
                    company_id=company_id,
                    total_price=total_price,
                    discounts=discounts,
                    refunds=refunds_total,
                    net_sales=total_price - discounts - refunds_total,
                    created_at=created_at,
                    source="shopify",
                    customer_id=customer_id,
                    customer_email_hash=customer_email_hash,
                    shipping_country=shipping_country,
                    shipping_region=shipping_region,
                    currency_code=currency_code,
                    sales_channel=sales_channel,
                    source_name=order.get("source_name"),
                    app_id=str(order.get("app_id") or "") or None,
                    referring_site=order.get("referring_site"),
                    landing_site=order.get("landing_site"),
                    order_tags=order.get("tags"),
                )
                db.add(order_row)
                db.flush()

            db.query(OrderLine).filter(
                OrderLine.order_id == order_row.id,
                OrderLine.company_id == company_id,
            ).delete()
            for line in order.get("line_items", []) or []:
                sku = line.get("sku") or line.get("variant_id") or "UNKNOWN"
                quantity = int(line.get("quantity") or 0)
                unit_price = float(line.get("price") or 0)
                product_name = line.get("title")
                product_type = line.get("product_type")
                if sku:
                    product = db.query(Product).filter(
                        Product.company_id == company_id,
                        Product.sku == str(sku),
                    ).first()
                    if product:
                        if product_name:
                            product.name = str(product_name)
                        if product_type:
                            product.product_type = str(product_type)
                    else:
                        db.add(Product(
                            company_id=company_id,
                            sku=str(sku),
                            name=str(product_name or sku),
                            product_type=str(product_type) if product_type else None,
                            unit_cost=0.0,
                        ))
                db.add(OrderLine(
                    order_id=order_row.id,
                    company_id=company_id,
                    sku=str(sku),
                    quantity=quantity,
                    unit_price=unit_price,
                    product_name=str(product_name) if product_name else None,
                    product_type=str(product_type) if product_type else None,
                ))

            for refund in order.get("refunds", []):
                refund_created_raw = refund.get("created_at") or created_at.isoformat()
                refund_created = datetime.fromisoformat(refund_created_raw.replace("Z", "+00:00"))
                if shift_demo_orders:
                    refund_created = refund_created - timedelta(days=1)
                amount = float(refund.get("amount") or 0)
                exists = db.query(Refund).filter(
                    Refund.order_id == order_row.id,
                    Refund.company_id == company_id,
                    Refund.created_at == refund_created,
                    Refund.amount == amount,
                ).first()
                if not exists:
                    db.add(Refund(
                        order_id=order_row.id,
                        company_id=company_id,
                        amount=amount,
                        created_at=refund_created,
                    ))
        inventory = fetch_inventory(shop_domain, access_token)
        today = datetime.now(timezone.utc).date()
        refunded_qty = sum(int(refund.get("quantity") or 0) for order in orders for refund in order.get("refunds", []))
        for item in inventory:
            db.add(InventorySnapshot(
                company_id=company_id,
                sku=str(item.get("inventory_item_id")),
                on_hand=int(item.get("available") or 0),
                snapshot_date=today,
                source="shopify",
            ))
        if refunded_qty > 0:
            db.query(InventorySnapshot).filter(
                InventorySnapshot.sku == "REFUNDED_ITEMS",
                InventorySnapshot.snapshot_date == today,
                InventorySnapshot.company_id == company_id,
            ).delete()
            db.add(InventorySnapshot(
                company_id=company_id,
                sku="REFUNDED_ITEMS",
                on_hand=refunded_qty,
                snapshot_date=today,
                source="shopify",
            ))
        db.commit()
        recompute_alerts(db, company_id)
        return "ok"
    finally:
        db.close()


@celery.task
def recompute_metrics(company_id: int):
    db: Session = SessionLocal()
    try:
        recompute_alerts(db, company_id)
        return "ok"
    finally:
        db.close()


@celery.task
def process_document(document_id: int):
    db: Session = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return "not_found"
        document.status = "processing"
        document.error_message = None
        db.commit()
        chunks = ingest_document(db, document_id)
        document.indexed_chunks = chunks
        document.indexed_at = datetime.now(timezone.utc)
        document.status = "indexed"
        db.commit()
        return "ok"
    except Exception as exc:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = "error"
            document.error_message = str(exc)
            db.commit()
        raise
    finally:
        db.close()


@celery.task
def reindex_documents(company_id: int):
    db: Session = SessionLocal()
    try:
        documents = db.query(Document).filter(Document.company_id == company_id).all()
        for document in documents:
            document.status = "queued"
            document.error_message = None
            document.indexed_chunks = 0
            document.indexed_at = None
        db.commit()
        for document in documents:
            process_document.delay(document.id)
        return {"queued": len(documents)}
    finally:
        db.close()


@celery.task
def wise_full_sync(company_id: int, environment: str):
    db: Session = SessionLocal()
    if not try_advisory_lock(db, company_id, "wise", environment):
        return "locked"
    run = start_sync_run(db, company_id, "wise", environment)
    counts = {}
    try:
        connector = WiseConnector(db, company_id, environment)
        counts["profiles"] = connector.sync_profiles()
        counts["balance_accounts"] = connector.sync_balance_accounts()
        counts["balances"] = connector.sync_balances()
        counts["transactions"] = connector.sync_transactions()
        connector.register_webhooks()
        creds = db.query(IntegrationCredentialWise).filter(
            IntegrationCredentialWise.company_id == company_id,
            IntegrationCredentialWise.wise_environment == environment,
        ).first()
        if creds:
            creds.last_sync_at = datetime.now(timezone.utc)
            db.commit()
        finish_sync_run(db, run.id, "success", counts)
        log_event(db, company_id, "wise.sync.completed", "sync_run", str(run.id), None, counts)
        return "ok"
    except Exception as exc:
        finish_sync_run(db, run.id, "failed", counts, str(exc))
        log_event(db, company_id, "wise.sync.failed", "sync_run", str(run.id), None, {"error": str(exc)})
        raise
    finally:
        release_advisory_lock(db, company_id, "wise", environment)
        db.close()


@celery.task
def wise_incremental_sync(company_id: int, subscription_id: str | None = None):
    db: Session = SessionLocal()
    environment = "sandbox"
    creds = db.query(IntegrationCredentialWise).filter(
        IntegrationCredentialWise.company_id == company_id,
    ).first()
    if creds:
        environment = creds.wise_environment
    if not try_advisory_lock(db, company_id, "wise", environment):
        return "locked"
    run = start_sync_run(db, company_id, "wise", environment)
    counts = {}
    try:
        connector = WiseConnector(db, company_id, environment)
        counts["balances"] = connector.sync_balances()
        counts["transactions"] = connector.sync_transactions()
        finish_sync_run(db, run.id, "success", counts)
        log_event(db, company_id, "wise.sync.incremental", "sync_run", str(run.id), None, {"subscription_id": subscription_id})
        return "ok"
    except Exception as exc:
        finish_sync_run(db, run.id, "failed", counts, str(exc))
        log_event(db, company_id, "wise.sync.incremental_failed", "sync_run", str(run.id), None, {"error": str(exc)})
        raise
    finally:
        release_advisory_lock(db, company_id, "wise", environment)
        db.close()


@celery.task
def wise_refresh_transfers(company_id: int, subscription_id: str | None = None):
    db: Session = SessionLocal()
    try:
        log_event(db, company_id, "wise.transfers.refresh", "webhook", subscription_id or "unknown", None, {})
        return "ok"
    finally:
        db.close()
