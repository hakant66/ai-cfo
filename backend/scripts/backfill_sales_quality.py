import argparse
import hashlib
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.integrations.shopify import fetch_orders
from app.models.models import Company, Integration, IntegrationType, Order, OrderLine, Product


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
        return "Marketplace"
    if "etsy" in tags or "etsy" in referring_site or "etsy" in landing_site:
        return "Marketplace"
    if source_name in {"web", "online_store", "shopify"}:
        return "DTC"
    return "Unknown"


def parse_created_at(raw: str | None) -> datetime:
    created_at_raw = raw or datetime.now(timezone.utc).isoformat()
    return datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))


def backfill(company_name: str, shop_domain: str | None, access_token: str | None, create_missing: bool) -> None:
    db: Session = SessionLocal()
    try:
        company = db.query(Company).filter(Company.name == company_name).first()
        if not company:
            raise SystemExit(f"Company not found: {company_name}")

        integration = db.query(Integration).filter(
            Integration.company_id == company.id,
            Integration.type == IntegrationType.shopify,
        ).first()

        if not shop_domain or not access_token:
            if not integration or not integration.credentials:
                raise SystemExit("Missing shop_domain/access_token and no Shopify integration configured.")
            creds = integration.credentials or {}
            shop_domain = creds.get("shop_domain")
            access_token = creds.get("access_token")

        if not shop_domain or not access_token:
            raise SystemExit("shop_domain and access_token are required.")

        orders = fetch_orders(shop_domain, access_token)
        updated = 0
        created = 0
        line_items_written = 0

        for payload in orders:
            external_id_raw = str(payload.get("id"))
            alt_external_id = f"{company.id}:{external_id_raw}"
            existing = db.query(Order).filter(
                Order.external_id.in_([external_id_raw, alt_external_id]),
                Order.company_id == company.id,
            ).first()
            external_id = external_id_raw
            if not existing and not create_missing:
                continue

            if not existing:
                conflict = db.query(Order).filter(
                    Order.external_id == external_id_raw,
                    Order.company_id != company.id,
                ).first()
                if conflict:
                    external_id = alt_external_id

            created_at = parse_created_at(payload.get("created_at"))
            total_price = float(payload.get("total_price") or 0)
            discounts = float(payload.get("total_discounts") or 0)
            refunds_total = sum(float(refund.get("amount") or 0) for refund in payload.get("refunds", []))
            customer = payload.get("customer") or {}
            shipping = payload.get("shipping_address") or {}
            sales_channel = infer_sales_channel(payload)

            if not existing:
                existing = Order(
                    external_id=external_id,
                    company_id=company.id,
                    total_price=total_price,
                    discounts=discounts,
                    refunds=refunds_total,
                    net_sales=total_price - discounts - refunds_total,
                    created_at=created_at,
                    source="shopify",
                )
                db.add(existing)
                db.flush()
                created += 1
            else:
                existing.total_price = total_price
                existing.discounts = discounts
                existing.refunds = refunds_total
                existing.net_sales = total_price - discounts - refunds_total
                if existing.created_at is None:
                    existing.created_at = created_at
                updated += 1

            existing.customer_id = customer.get("id")
            existing.customer_email_hash = hash_email(payload.get("email") or customer.get("email"))
            existing.shipping_country = shipping.get("country_code") or shipping.get("countryCode") or shipping.get("country")
            existing.shipping_region = shipping.get("province_code") or shipping.get("provinceCode") or shipping.get("province")
            existing.currency_code = payload.get("currency") or payload.get("currency_code")
            existing.sales_channel = sales_channel
            existing.source_name = payload.get("source_name")
            existing.app_id = str(payload.get("app_id") or "") or None
            existing.referring_site = payload.get("referring_site")
            existing.landing_site = payload.get("landing_site")
            existing.order_tags = payload.get("tags")

            db.query(OrderLine).filter(OrderLine.order_id == existing.id).delete()
            for line in payload.get("line_items", []) or []:
                sku = line.get("sku") or line.get("variant_id") or "UNKNOWN"
                quantity = int(line.get("quantity") or 0)
                unit_price = float(line.get("price") or 0)
                product_name = line.get("title")
                product_type = line.get("product_type")

                if sku:
                    product = db.query(Product).filter(
                        Product.company_id == company.id,
                        Product.sku == str(sku),
                    ).first()
                    if product:
                        if product_name:
                            product.name = str(product_name)
                        if product_type:
                            product.product_type = str(product_type)
                    else:
                        db.add(Product(
                            company_id=company.id,
                            sku=str(sku),
                            name=str(product_name or sku),
                            product_type=str(product_type) if product_type else None,
                            unit_cost=0.0,
                        ))

                db.add(OrderLine(
                    order_id=existing.id,
                    company_id=company.id,
                    sku=str(sku),
                    quantity=quantity,
                    unit_price=unit_price,
                    product_name=str(product_name) if product_name else None,
                    product_type=str(product_type) if product_type else None,
                ))
                line_items_written += 1

        db.commit()
        print(f"Backfill complete for {company.name}. Updated: {updated}, Created: {created}, Lines: {line_items_written}.")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill sales quality fields from Shopify payloads.")
    parser.add_argument("--company-name", required=True, help="Company name to backfill.")
    parser.add_argument("--shop-domain", help="Shopify shop domain (overrides integration).")
    parser.add_argument("--access-token", help="Shopify access token (overrides integration).")
    parser.add_argument("--create-missing", action="store_true", help="Create orders when no matching external_id exists.")
    args = parser.parse_args()
    backfill(args.company_name, args.shop_domain, args.access_token, args.create_missing)


if __name__ == "__main__":
    main()
