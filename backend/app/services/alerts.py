from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.models import Alert, AlertType, AlertSeverity, MarketingSpend, Order, Refund, InventorySnapshot


def recompute_alerts(db: Session, company_id: int) -> list[Alert]:
    db.query(Alert).filter(Alert.company_id == company_id).delete()
    alerts: list[Alert] = []

    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)

    spend_recent = db.query(MarketingSpend).filter(
        MarketingSpend.company_id == company_id,
        MarketingSpend.spend_date >= week_ago,
    ).all()
    spend_yesterday = sum(s.amount for s in spend_recent if s.spend_date == yesterday)
    spend_week_avg = sum(s.amount for s in spend_recent) / 7 if spend_recent else 0
    if spend_week_avg > 0 and spend_yesterday > spend_week_avg * 1.5:
        alerts.append(Alert(
            company_id=company_id,
            alert_type=AlertType.spend_spike,
            severity=AlertSeverity.medium,
            message="Ad spend spiked vs 7-day average.",
            metadata_json={"yesterday": spend_yesterday, "avg_7d": spend_week_avg},
        ))

    orders_last_7d = db.query(Order).filter(
        Order.company_id == company_id,
        Order.created_at >= datetime.now(timezone.utc) - timedelta(days=7),
    ).count()
    orders_prev_7d = db.query(Order).filter(
        Order.company_id == company_id,
        Order.created_at >= datetime.now(timezone.utc) - timedelta(days=14),
        Order.created_at < datetime.now(timezone.utc) - timedelta(days=7),
    ).count()
    if orders_prev_7d > 0 and orders_last_7d < orders_prev_7d * 0.7:
        alerts.append(Alert(
            company_id=company_id,
            alert_type=AlertType.conversion_drop,
            severity=AlertSeverity.high,
            message="Order volume dropped vs prior week.",
            metadata_json={"last_7d": orders_last_7d, "prev_7d": orders_prev_7d},
        ))

    refunds_last_7d = db.query(Refund).join(Order, Refund.order_id == Order.id).filter(
        Order.company_id == company_id,
        Refund.created_at >= datetime.now(timezone.utc) - timedelta(days=7),
    ).count()
    orders_last_7d = max(orders_last_7d, 1)
    refund_rate = refunds_last_7d / orders_last_7d
    if refund_rate > 0.1:
        alerts.append(Alert(
            company_id=company_id,
            alert_type=AlertType.return_rate_jump,
            severity=AlertSeverity.medium,
            message="Refund rate exceeded threshold.",
            metadata_json={"refund_rate": refund_rate},
        ))

    snapshots = db.query(InventorySnapshot).filter(
        InventorySnapshot.snapshot_date == today,
        InventorySnapshot.company_id == company_id,
    ).all()
    for snap in snapshots:
        if snap.on_hand <= 0:
            alerts.append(Alert(
                company_id=company_id,
                alert_type=AlertType.stockout_risk,
                severity=AlertSeverity.high,
                message=f"Stockout risk for SKU {snap.sku}.",
                metadata_json={"sku": snap.sku},
            ))

    for alert in alerts:
        db.add(alert)
    db.commit()
    return alerts
