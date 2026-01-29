from datetime import datetime, timezone

from app.integrations.shopify import fetch_products, fetch_orders
from app.models.models import Product, Company, Order, Refund


def test_mock_shopify_products_persist(db_session_postgres, mock_shopify_settings):
    products = fetch_products(None, None)
    assert isinstance(products, list)
    assert len(products) > 0

    company = db_session_postgres.query(Company).filter(Company.name == "Mock Shopify Co").first()
    if not company:
        company = Company(name="Mock Shopify Co", currency="USD", timezone="UTC", settlement_lag_days=2, thresholds={})
        db_session_postgres.add(company)
        db_session_postgres.commit()
        db_session_postgres.refresh(company)

    inserted = 0
    for product in products:
        sku = product.get("handle") or product.get("id")
        name = product.get("title") or product.get("id")
        if not sku or not name:
            continue
        db_session_postgres.add(
            Product(
                company_id=company.id,
                sku=str(sku),
                name=str(name),
                unit_cost=0.0,
            )
        )
        inserted += 1
    db_session_postgres.commit()

    stored = db_session_postgres.query(Product).count()
    assert stored >= inserted


def test_mock_shopify_orders_refunds_persist(db_session_postgres, mock_shopify_settings):
    orders = fetch_orders(None, None)
    assert isinstance(orders, list)
    assert len(orders) > 0

    company = db_session_postgres.query(Company).filter(Company.name == "Mock Shopify Co").first()
    if not company:
        company = Company(name="Mock Shopify Co", currency="USD", timezone="UTC", settlement_lag_days=2, thresholds={})
        db_session_postgres.add(company)
        db_session_postgres.commit()
        db_session_postgres.refresh(company)

    for order in orders:
        total_price = float(order.get("total_price") or 0)
        discounts = float(order.get("total_discounts") or 0)
        refunds_total = sum(float(refund.get("amount") or 0) for refund in order.get("refunds", []))
        created_at_raw = order.get("created_at") or datetime.now(timezone.utc).isoformat()
        created_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
        order_row = Order(
            external_id=str(order.get("id")),
            company_id=company.id,
            total_price=total_price,
            discounts=discounts,
            refunds=refunds_total,
            net_sales=total_price - discounts - refunds_total,
            created_at=created_at,
            source="shopify",
        )
        db_session_postgres.add(order_row)
        db_session_postgres.flush()
        for refund in order.get("refunds", []):
            refund_created_raw = refund.get("created_at") or created_at.isoformat()
            refund_created = datetime.fromisoformat(refund_created_raw.replace("Z", "+00:00"))
            db_session_postgres.add(
                Refund(
                    order_id=order_row.id,
                    company_id=company.id,
                    amount=float(refund.get("amount") or 0),
                    created_at=refund_created,
                )
            )

    db_session_postgres.commit()

    refund_count = db_session_postgres.query(Refund).count()
    assert refund_count >= 1
