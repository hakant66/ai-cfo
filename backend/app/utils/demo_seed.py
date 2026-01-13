from datetime import date

from sqlalchemy.orm import Session

from app.models import BankAccount, Bill, Company, Order


def seed_demo_company(db: Session) -> Company:
    company = Company(name="Demo Retail Co", currency="USD", timezone="UTC")
    db.add(company)
    db.flush()

    db.add(BankAccount(company_id=company.id, name="Main Checking", balance=42000, currency="USD"))
    db.add(Bill(company_id=company.id, vendor="Packaging Co", amount=2400, due_date=date.today(), priority="critical"))
    db.add(
        Order(
            company_id=company.id,
            external_id="DEMO-1001",
            total_gross=20000,
            total_discounts=500,
            total_refunds=300,
        )
    )
    db.commit()
    return company
