from datetime import datetime, timedelta, timezone

from app.models.models import BankAccount, Bill, Company, ExchangeRate, InventorySnapshot
from app.api.deps import require_roles
from app.models.models import Role, User
from fastapi import HTTPException
from app.schemas.auth import AdminUserCreate
from app.api.auth import admin_create_user
from app.services.exchange_rates import list_exchange_rates
from app.services.metrics import get_inventory_health, list_payables


def _seed_company(db_session, name: str) -> Company:
    company = Company(name=name, currency="USD", timezone="UTC", settlement_lag_days=2, thresholds={})
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


def test_inventory_health_scoped_to_company(db_session):
    company_a = _seed_company(db_session, "Alpha Co")
    company_b = _seed_company(db_session, "Beta Co")
    today = datetime.now(timezone.utc).date()

    db_session.add(InventorySnapshot(company_id=company_a.id, sku="SKU-A", on_hand=10, snapshot_date=today, source="manual"))
    db_session.add(InventorySnapshot(company_id=company_b.id, sku="SKU-B", on_hand=20, snapshot_date=today, source="manual"))
    db_session.commit()

    result = get_inventory_health(db_session, company_a.id)
    skus = {item["sku"] for item in result["items"]}
    assert skus == {"SKU-A"}


def test_payables_scoped_to_company(db_session):
    company_a = _seed_company(db_session, "Alpha Payables")
    company_b = _seed_company(db_session, "Beta Payables")

    db_session.add(Bill(company_id=company_a.id, vendor="Vendor A", amount=100, due_date=datetime.now(timezone.utc).date()))
    db_session.add(Bill(company_id=company_b.id, vendor="Vendor B", amount=200, due_date=datetime.now(timezone.utc).date()))
    db_session.commit()

    result = list_payables(db_session, company_a.id)
    vendors = {item["vendor"] for item in result["items"]}
    assert vendors == {"Vendor A"}


def test_exchange_rates_scoped_to_company(db_session):
    company_a = _seed_company(db_session, "Alpha FX")
    company_b = _seed_company(db_session, "Beta FX")

    db_session.add(ExchangeRate(company_id=company_a.id, pair="USD/GBP", rate=0.8, updated_at=datetime.now(timezone.utc)))
    db_session.add(ExchangeRate(company_id=company_b.id, pair="USD/GBP", rate=0.7, updated_at=datetime.now(timezone.utc) - timedelta(days=1)))
    db_session.commit()

    rates = list_exchange_rates(db_session, company_a.id)
    assert len(rates) == 1
    assert rates[0]["rate"] == 0.8


def test_companies_list_restricted_to_founder(db_session):
    company = _seed_company(db_session, "Alpha Admin")
    user = User(
        email="ops@example.com",
        password_hash="hash",
        role=Role.ops,
        company_id=company.id,
    )
    db_session.add(user)
    db_session.commit()

    guard = require_roles(["Founder"])
    try:
        guard(user)
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 403


def test_admin_user_create_requires_founder(db_session):
    company = _seed_company(db_session, "Users Co")
    founder = User(
        email="founder@example.com",
        password_hash="hash",
        role=Role.founder,
        company_id=company.id,
    )
    db_session.add(founder)
    db_session.commit()

    payload = AdminUserCreate(
        email="newuser@example.com",
        password="secret123",
        role=Role.finance,
        company_id=company.id,
    )
    created = admin_create_user(payload, db_session, founder)
    assert created.email == "newuser@example.com"

    ops_user = User(
        email="ops2@example.com",
        password_hash="hash",
        role=Role.ops,
        company_id=company.id,
    )
    try:
        admin_create_user(payload, db_session, ops_user)
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 403
