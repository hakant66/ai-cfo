import random
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import Company, User, Role, BankAccount, BankTransaction, Bill, InventorySnapshot, Order, MarketingSpend
from app.services.demo_data import DEMO_COMPANY_NAME
from app.core.security import get_password_hash


def seed():
    db: Session = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.email == "demo@aicfo.dev").first()
        if existing_user:
            company = db.query(Company).filter(Company.id == existing_user.company_id).first()
            if company:
                bank_account = db.query(BankAccount).filter(
                    BankAccount.company_id == company.id,
                    BankAccount.provider.in_(["manual", None]),
                ).first()
                if not bank_account:
                    bank_account = BankAccount(company_id=company.id, name="Operating", currency="USD", provider="manual")
                    db.add(bank_account)
                bank_account.balance = 35000
                bank_account.provider = "manual"
                wise_account = db.query(BankAccount).filter(
                    BankAccount.company_id == company.id,
                    BankAccount.provider == "wise",
                    BankAccount.provider_account_id == "wise-demo-1",
                ).first()
                if not wise_account:
                    wise_account = BankAccount(
                        company_id=company.id,
                        name="Wise Treasury",
                        currency="USD",
                        provider="wise",
                        provider_account_id="wise-demo-1",
                    )
                    db.add(wise_account)
                wise_account.balance = 90000
                db.commit()
                print("Demo balances updated.")
                return
            print("Demo user already exists. Skipping seed.")
            return
        legacy_user = db.query(User).filter(User.email == "demo@aicfo.local").first()
        if legacy_user:
            legacy_user.email = "demo@aicfo.dev"
            db.commit()
            print("Updated demo user email to demo@aicfo.dev.")
            return

        company = Company(name="Demo Retail Co", currency="USD", timezone="UTC", settlement_lag_days=2, thresholds={"stockout_weeks": 2, "overstock_weeks": 12})
        db.add(company)
        db.flush()

        user = User(email="demo@aicfo.dev", password_hash=get_password_hash("aicfo12345"), role=Role.founder, company_id=company.id)
        db.add(user)

        account = BankAccount(company_id=company.id, name="Operating", currency="USD", balance=125000)
        db.add(account)
        db.flush()

        for i in range(30):
            db.add(BankTransaction(
                bank_account_id=account.id,
                company_id=company.id,
                posted_at=(datetime.now(timezone.utc) - timedelta(days=i)).date(),
                amount=random.uniform(-1200, 1800),
                description="Daily activity",
                category="operations",
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

        for i in range(20):
            total = random.uniform(120, 900)
            discounts = random.uniform(0, 50)
            refunds = random.uniform(0, 20)
            db.add(Order(
                external_id=f"demo-order-{i}",
                company_id=company.id,
                total_price=total,
                discounts=discounts,
                refunds=refunds,
                net_sales=total - discounts - refunds,
                created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(0, 3)),
                source="shopify",
            ))

        for i in range(7):
            db.add(MarketingSpend(
                company_id=company.id,
                source="manual",
                spend_date=(datetime.now(timezone.utc) - timedelta(days=i)).date(),
                amount=random.uniform(200, 800),
            ))

        db.commit()
        print("Seeded demo company.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
