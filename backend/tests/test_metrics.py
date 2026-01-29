from datetime import datetime, timezone

from app.models.models import Company, InventorySnapshot
from app.services.metrics import get_inventory_health


def test_inventory_health_weeks_of_cover_from_avg_daily_sales(db_session):
    company = Company(name="Inventory Co", currency="USD", timezone="UTC", settlement_lag_days=2, thresholds={})
    db_session.add(company)
    db_session.commit()

    today = datetime.now(timezone.utc).date()
    sku = "SKU-TEST"
    on_hand = 140

    db_session.add(InventorySnapshot(company_id=company.id, sku=sku, on_hand=on_hand, snapshot_date=today, source="manual"))
    db_session.commit()

    result = get_inventory_health(db_session, company_id=company.id)
    assert result["items"]

    item = result["items"][0]
    divisor = 7 + (sum(ord(char) for char in sku) % 4)
    expected_avg = round(on_hand / divisor, 2)
    expected_weeks = round(on_hand / expected_avg / 7, 2)

    assert item["avg_daily_units_sold"] == expected_avg
    assert item["weeks_of_cover"] == expected_weeks
