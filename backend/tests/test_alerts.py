from datetime import datetime, timedelta, timezone
from app.services.alerts import recompute_alerts
from app.models.models import MarketingSpend, Order, Refund, InventorySnapshot, Company


def test_alert_generation(db_session):
    company = Company(name="Demo", currency="USD", timezone="UTC", settlement_lag_days=2, thresholds={})
    db_session.add(company)
    db_session.commit()

    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    db_session.add(MarketingSpend(company_id=company.id, source="manual", spend_date=yesterday, amount=1500))
    for idx in range(7):
        db_session.add(MarketingSpend(company_id=company.id, source="manual", spend_date=today - timedelta(days=idx), amount=200))

    for idx in range(5):
        db_session.add(Order(
            external_id=f"order{idx}",
            company_id=company.id,
            total_price=100,
            discounts=0,
            refunds=0,
            net_sales=100,
            created_at=datetime.now(timezone.utc) - timedelta(days=3),
            source="shopify",
        ))
    db_session.commit()

    first_order = db_session.query(Order).first()
    db_session.add(Refund(order_id=first_order.id, company_id=company.id, amount=20, created_at=datetime.now(timezone.utc)))
    db_session.add(InventorySnapshot(company_id=company.id, sku="SKU-1", on_hand=0, snapshot_date=today, source="manual"))
    db_session.commit()

    alerts = recompute_alerts(db_session, company.id)
    alert_types = {a.alert_type.value for a in alerts}
    assert "SpendSpike" in alert_types
    assert "ReturnRateJump" in alert_types
    assert "StockoutRisk" in alert_types
