import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.models import (
    BankAccount,
    BankTransaction,
    Bill,
    Company,
    Integration,
    IntegrationType,
    InventorySnapshot,
    MarketingSpend,
    Order,
    OrderLine,
    Refund,
    Role,
    User,
)

DEMO_COMPANY_NAME = "Demo Retail Co"
DEMO_EMAIL = "demo@aicfo.dev"
DEMO_PASSWORD = "aicfo12345"
DEMO_SHOP_DOMAIN = "mock-shopify:8080"
DEMO_SHOP_TOKEN = "mock_token_123"


def _get_or_create_demo_company(db: Session) -> Company:
    company = db.query(Company).filter(Company.name == DEMO_COMPANY_NAME).first()
    if company:
        return company
    company = Company(
        name=DEMO_COMPANY_NAME,
        currency="USD",
        timezone="UTC",
        settlement_lag_days=2,
        thresholds={"stockout_weeks": 2, "overstock_weeks": 12},
    )
    db.add(company)
    db.flush()
    return company


def _ensure_demo_user(db: Session, company: Company) -> None:
    user = db.query(User).filter(User.email == DEMO_EMAIL).first()
    if user:
        if user.company_id != company.id:
            user.company_id = company.id
            user.role = Role.founder
        return
    db.add(User(
        email=DEMO_EMAIL,
        password_hash=get_password_hash(DEMO_PASSWORD),
        role=Role.founder,
        company_id=company.id,
    ))


def _clear_company_data(db: Session, company_id: int) -> None:
    db.query(OrderLine).filter(OrderLine.order_id.in_(
        db.query(Order.id).filter(Order.company_id == company_id)
    )).delete(synchronize_session=False)
    db.query(Refund).filter(Refund.order_id.in_(
        db.query(Order.id).filter(Order.company_id == company_id)
    )).delete(synchronize_session=False)
    db.query(Order).filter(Order.company_id == company_id).delete(synchronize_session=False)

    db.query(BankTransaction).filter(
        BankTransaction.bank_account_id.in_(db.query(BankAccount.id).filter(BankAccount.company_id == company_id))
    ).delete(synchronize_session=False)
    db.query(BankAccount).filter(BankAccount.company_id == company_id).delete(synchronize_session=False)
    db.query(Bill).filter(Bill.company_id == company_id).delete(synchronize_session=False)
    db.query(MarketingSpend).filter(MarketingSpend.company_id == company_id).delete(synchronize_session=False)

    db.query(InventorySnapshot).filter(
        InventorySnapshot.company_id == company_id,
        InventorySnapshot.sku.in_(["SKU-100", "SKU-200", "SKU-300"]),
    ).delete(synchronize_session=False)


def _seed_company_basics(db: Session, company: Company) -> None:
    account = BankAccount(company_id=company.id, name="Operating", currency="USD", balance=35000, provider="manual")
    db.add(account)
    db.flush()

    for i in range(30):
        db.add(BankTransaction(
            bank_account_id=account.id,
            company_id=company.id,
            posted_at=(datetime.now(timezone.utc) - timedelta(days=i)).date(),
            amount=random.uniform(-1200, 1800),
            currency="USD",
            description="Daily activity",
            category="operations",
            provider="manual",
        ))

    for i in range(10):
        db.add(Bill(
            company_id=company.id,
            vendor=f"Supplier {i}",
            amount=random.uniform(500, 3000),
            due_date=(datetime.now(timezone.utc) + timedelta(days=i)).date(),
            status="open",
            criticality="critical" if i < 3 else "deferrable",
        ))

    for sku in ["SKU-100", "SKU-200", "SKU-300"]:
        db.add(InventorySnapshot(
            company_id=company.id,
            sku=sku,
            on_hand=random.randint(0, 200),
            snapshot_date=datetime.now(timezone.utc).date(),
            source="demo",
        ))

    for i in range(7):
        db.add(MarketingSpend(
            company_id=company.id,
            source="manual",
            spend_date=(datetime.now(timezone.utc) - timedelta(days=i)).date(),
            amount=random.uniform(200, 800),
        ))

    wise_account = BankAccount(
        company_id=company.id,
        name="Wise Treasury",
        currency="USD",
        balance=90000,
        provider="wise",
        provider_account_id="wise-demo-1",
    )
    db.add(wise_account)
    db.flush()


def _seed_historic_orders(db: Session, company: Company) -> None:
    today = datetime.now(timezone.utc).date()
    base_orders = random.randint(8, 14)
    base_aov = random.uniform(60, 140)
    base_discount_pct = random.uniform(0.03, 0.12)
    base_refund_pct = random.uniform(0.0, 0.04)

    sku_catalog = [
        {"sku": "SKU-100", "name": "Luna Carryall", "type": "Bags", "price": 48},
        {"sku": "SKU-200", "name": "Noir Crossbody", "type": "Bags", "price": 62},
        {"sku": "SKU-300", "name": "Atlas Duffel", "type": "Bags", "price": 89},
        {"sku": "SKU-400", "name": "Meridian Wallet", "type": "Accessories", "price": 32},
        {"sku": "SKU-500", "name": "Summit Belt", "type": "Accessories", "price": 28},
    ]
    channels = ["Online Store", "Amazon", "Wholesale", "Retail"]
    shipping_profiles = [
        ("US", "CA", "USD", 0.6),
        ("US", "NY", "USD", 0.2),
        ("UK", "London", "GBP", 0.1),
        ("DE", "Berlin", "EUR", 0.1),
    ]
    customers = [f"cust-{idx}" for idx in range(1, 201)]

    for day_offset in range(1, 366):
        day = today - timedelta(days=day_offset)
        day_factor = random.uniform(0.9, 1.1)
        orders_count = max(1, int(round(base_orders * day_factor)))

        for order_idx in range(orders_count):
            order_factor = random.uniform(0.9, 1.1)
            order_total = base_aov * day_factor * order_factor
            discounts = order_total * base_discount_pct * random.uniform(0.8, 1.2)
            refunds = order_total * base_refund_pct * random.uniform(0.8, 1.2)
            net_sales = max(order_total - discounts - refunds, 0)

            created_at = datetime.combine(day, datetime.min.time()) + timedelta(
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )
            country, region, currency = random.choices(
                [(c, r, cur) for c, r, cur, _ in shipping_profiles],
                weights=[weight for _, _, _, weight in shipping_profiles],
                k=1,
            )[0]
            order = Order(
                external_id=f"demo-order-{day_offset}-{order_idx}",
                company_id=company.id,
                total_price=round(order_total, 2),
                discounts=round(discounts, 2),
                refunds=round(refunds, 2),
                net_sales=round(net_sales, 2),
                created_at=created_at,
                source="Shopify",
                customer_id=random.choice(customers),
                shipping_country=country,
                shipping_region=region,
                currency_code=currency,
                sales_channel=random.choice(channels),
                source_name="demo_seed",
            )
            db.add(order)
            db.flush()

            lines_count = random.randint(1, 3)
            for _ in range(lines_count):
                item = random.choice(sku_catalog)
                quantity = random.randint(1, 3)
                unit_price = item["price"] * random.uniform(0.9, 1.1)
                db.add(OrderLine(
                    order_id=order.id,
                    company_id=company.id,
                    sku=item["sku"],
                    quantity=quantity,
                    unit_price=round(unit_price, 2),
                    product_name=item["name"],
                    product_type=item["type"],
                ))

            if refunds > 0:
                db.add(Refund(
                    order_id=order.id,
                    company_id=company.id,
                    amount=round(refunds, 2),
                    created_at=created_at + timedelta(hours=random.randint(1, 48)),
                ))


def _ensure_shopify_integration(db: Session, company: Company) -> None:
    integration = db.query(Integration).filter(
        Integration.company_id == company.id,
        Integration.type == IntegrationType.shopify,
    ).first()
    creds = {"shop_domain": DEMO_SHOP_DOMAIN, "access_token": DEMO_SHOP_TOKEN}
    if not integration:
        db.add(Integration(
            company_id=company.id,
            type=IntegrationType.shopify,
            status="connected",
            credentials=creds,
        ))
    else:
        integration.status = "connected"
        integration.credentials = creds


def reseed_demo_data(db: Session) -> Company:
    company = _get_or_create_demo_company(db)
    _ensure_demo_user(db, company)
    _clear_company_data(db, company.id)
    _seed_company_basics(db, company)
    _seed_historic_orders(db, company)
    _ensure_shopify_integration(db, company)
    db.commit()
    return company


def reseed_company_demo_data(db: Session, company_id: int) -> Company:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise ValueError("Company not found")
    _clear_company_data(db, company.id)
    _seed_company_basics(db, company)
    _seed_historic_orders(db, company)
    _ensure_shopify_integration(db, company)
    db.commit()
    return company


def clear_company_demo_data(db: Session, company_id: int) -> Company:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise ValueError("Company not found")
    _clear_company_data(db, company.id)
    db.commit()
    return company
