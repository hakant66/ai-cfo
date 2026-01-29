from datetime import date, datetime, timedelta

from app.models.models import Company, Order, OrderLine
from app.services.sales_quality import calculate_aov, calculate_upo, get_sales_quality


def _seed_company(db_session):
    company = Company(name="Sales Quality Co", currency="USD", timezone="UTC", settlement_lag_days=2, thresholds={})
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


def test_aov_calculation():
    assert calculate_aov(200.0, 4) == 50.0
    assert calculate_aov(0.0, 0) is None


def test_upo_calculation():
    assert calculate_upo(10, 5) == 2.0
    assert calculate_upo(0, 0) is None


def test_new_vs_returning_classification(db_session):
    company = _seed_company(db_session)
    window_date = date(2026, 1, 10)
    prior_date = datetime(2026, 1, 9, 10, 0, 0)
    in_window = datetime(2026, 1, 10, 12, 0, 0)

    db_session.add(Order(
        company_id=company.id,
        external_id="order-old",
        total_price=100.0,
        discounts=0.0,
        refunds=0.0,
        net_sales=100.0,
        created_at=prior_date,
        source="shopify",
        customer_id="cust-1",
    ))
    db_session.add(Order(
        company_id=company.id,
        external_id="order-return",
        total_price=120.0,
        discounts=0.0,
        refunds=0.0,
        net_sales=120.0,
        created_at=in_window,
        source="shopify",
        customer_id="cust-1",
    ))
    db_session.add(Order(
        company_id=company.id,
        external_id="order-new",
        total_price=80.0,
        discounts=0.0,
        refunds=0.0,
        net_sales=80.0,
        created_at=in_window + timedelta(hours=1),
        source="shopify",
        customer_id="cust-2",
    ))
    db_session.commit()

    result = get_sales_quality(db_session, company.id, window_date, window_date)
    new_orders = result["new_vs_returning"]["new_customer_orders"]["value"]
    returning_orders = result["new_vs_returning"]["returning_customer_orders"]["value"]
    repeat_rate = result["new_vs_returning"]["repeat_purchase_rate"]["value"]

    assert new_orders == 1
    assert returning_orders == 1
    assert repeat_rate == 50.0


def test_top10_sku_share(db_session):
    company = _seed_company(db_session)
    window_date = date(2026, 1, 12)
    created_at = datetime(2026, 1, 12, 9, 0, 0)

    order = Order(
        company_id=company.id,
        external_id="order-1",
        total_price=200.0,
        discounts=0.0,
        refunds=0.0,
        net_sales=200.0,
        created_at=created_at,
        source="shopify",
    )
    db_session.add(order)
    db_session.flush()
    db_session.add(OrderLine(order_id=order.id, company_id=company.id, sku="SKU-1", quantity=2, unit_price=50.0))
    db_session.add(OrderLine(order_id=order.id, company_id=company.id, sku="SKU-2", quantity=1, unit_price=100.0))
    db_session.commit()

    result = get_sales_quality(db_session, company.id, window_date, window_date)
    top10_share = result["kpis"]["top10_sku_share"]["value"]
    assert top10_share == 100.0


def test_top10_sku_share_capped_at_100(db_session):
    company = _seed_company(db_session)
    window_date = date(2026, 1, 15)
    created_at = datetime(2026, 1, 15, 10, 0, 0)

    order = Order(
        company_id=company.id,
        external_id="order-cap",
        total_price=200.0,
        discounts=50.0,
        refunds=50.0,
        net_sales=100.0,
        created_at=created_at,
        source="shopify",
    )
    db_session.add(order)
    db_session.flush()
    db_session.add(OrderLine(order_id=order.id, company_id=company.id, sku="SKU-A", quantity=2, unit_price=60.0))
    db_session.add(OrderLine(order_id=order.id, company_id=company.id, sku="SKU-B", quantity=1, unit_price=80.0))
    db_session.commit()

    result = get_sales_quality(db_session, company.id, window_date, window_date)
    top10_share = result["kpis"]["top10_sku_share"]["value"]
    assert top10_share == 100.0
