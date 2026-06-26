import json

import pytest
import stripe
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.main import app
from app.models.models import Company, Integration, IntegrationType, Role, StripeMetric, StripeWebhookEvent, User
from app.services import stripe_webhook_incremental as stripe_wh_inc
from app.services.stripe_webhook_incremental import (
    build_synthetic_stripe_event,
    persist_stripe_webhook_event,
    process_stripe_webhook_row,
    resolve_company_id,
)


@pytest.fixture()
def stripe_company(db_session: Session) -> Company:
    company = Company(name="Stripe Webhook Co")
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


def test_stripe_api_echo_skipped_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "stripe_api_echo_after_synthetic", False)
    from app.services.stripe_webhook_incremental import _stripe_api_health_echo

    assert _stripe_api_health_echo() == {"skipped": True}


def test_resolve_company_from_connect_account(db_session: Session, stripe_company: Company):
    db_session.add(
        Integration(
            company_id=stripe_company.id,
            type=IntegrationType.stripe,
            status="connected",
            credentials={"stripe_account": "acct_test123"},
        )
    )
    db_session.commit()
    event = {"account": "acct_test123", "type": "payout.paid", "data": {"object": {}}}
    assert resolve_company_id(db_session, event) == stripe_company.id


def test_resolve_company_from_metadata(db_session: Session, stripe_company: Company):
    db_session.add(
        Integration(
            company_id=stripe_company.id,
            type=IntegrationType.stripe,
            status="connected",
            credentials={},
        )
    )
    db_session.commit()
    event = {
        "type": "charge.failed",
        "data": {"object": {"metadata": {"aicfo_company_id": str(stripe_company.id)}}},
    }
    assert resolve_company_id(db_session, event) == stripe_company.id


def test_persist_webhook_idempotent(db_session: Session, stripe_company: Company):
    ev = build_synthetic_stripe_event("payout.paid", stripe_company.id)
    row1, dup1 = persist_stripe_webhook_event(db_session, company_id=stripe_company.id, event_dict=ev)
    assert dup1 is False
    assert row1 is not None
    row2, dup2 = persist_stripe_webhook_event(db_session, company_id=stripe_company.id, event_dict=ev)
    assert dup2 is True
    assert row2 is None
    assert db_session.query(StripeWebhookEvent).count() == 1


def test_process_synthetic_webhook_row(db_session: Session, stripe_company: Company):
    ev = build_synthetic_stripe_event("refund.created", stripe_company.id)
    row, _ = persist_stripe_webhook_event(db_session, company_id=stripe_company.id, event_dict=ev)
    assert row is not None
    out = process_stripe_webhook_row(db_session, row.id)
    assert out["mode"] == "synthetic"
    assert out["inserted"] == 1
    assert db_session.query(StripeMetric).filter(StripeMetric.company_id == stripe_company.id).count() == 1
    row2 = db_session.query(StripeWebhookEvent).filter(StripeWebhookEvent.id == row.id).first()
    assert row2 is not None
    assert row2.processed_at is not None


def _stripe_test_signature_header(payload_bytes: bytes, secret: str) -> str:
    import hashlib
    import hmac
    import time

    payload_str = payload_bytes.decode("utf-8")
    ts = int(time.time())
    signed_payload = f"{ts}.{payload_str}"
    digest = hmac.new(secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


def test_stripe_webhook_construct_event(monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test_secret_for_unit_tests_only")
    payload_dict = {
        "id": "evt_construct_test",
        "object": "event",
        "type": "charge.failed",
        "livemode": False,
        "data": {"object": {"id": "ch_x", "amount": 100, "currency": "usd", "metadata": {"aicfo_company_id": "1"}}},
    }
    payload = json.dumps(payload_dict).encode("utf-8")
    header = _stripe_test_signature_header(payload, settings.stripe_webhook_secret)
    event = stripe.Webhook.construct_event(payload, header, settings.stripe_webhook_secret, tolerance=300)
    assert stripe_event_to_dict_safe(event)["id"] == "evt_construct_test"


def stripe_event_to_dict_safe(event):
    fn = getattr(event, "to_dict", None)
    if callable(fn):
        return fn()
    return dict(event)


def test_mock_endpoint_requires_secret(db_session: Session, stripe_company: Company, monkeypatch):
    monkeypatch.setattr(settings, "mock_stripe_webhook_secret", "mock-secret-xyz")

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        res = client.post(
            "/webhooks/stripe/mock",
            json={"company_id": stripe_company.id, "scenario": "payout.paid"},
            headers={"X-Mock-Stripe-Secret": "wrong"},
        )
        assert res.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_mock_unknown_company_returns_404(db_session: Session, monkeypatch):
    monkeypatch.setattr(settings, "mock_stripe_webhook_secret", "mock-secret-xyz")

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        res = client.post(
            "/webhooks/stripe/mock",
            json={"company_id": 999_999, "scenario": "refund.created"},
            headers={"X-Mock-Stripe-Secret": "mock-secret-xyz"},
        )
        assert res.status_code == 404
        assert "999999" in res.json().get("detail", "")
    finally:
        app.dependency_overrides.clear()


def test_mock_endpoint_inserts_metric(db_session: Session, stripe_company: Company, monkeypatch):
    monkeypatch.setattr(settings, "mock_stripe_webhook_secret", "mock-secret-xyz")

    def override_db():
        yield db_session

    def fake_enqueue(webhook_pk: int):
        process_stripe_webhook_row(db_session, webhook_pk)
        return True, None

    monkeypatch.setattr(stripe_wh_inc, "enqueue_stripe_webhook_incremental_task", fake_enqueue)

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        res = client.post(
            "/webhooks/stripe/mock",
            json={"company_id": stripe_company.id, "scenario": "charge.failed"},
            headers={"X-Mock-Stripe-Secret": "mock-secret-xyz"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["received"] is True
        assert data["queued"] is True
        assert db_session.query(StripeMetric).filter(StripeMetric.company_id == stripe_company.id).count() == 1
    finally:
        app.dependency_overrides.clear()


def test_connectors_dev_mock_returns_404_when_disabled(db_session: Session, stripe_company: Company, monkeypatch):
    monkeypatch.setattr(settings, "stripe_dev_mock_ui_enabled", False)
    user = User(
        email="devmock@test.dev",
        password_hash="x",
        role=Role.founder,
        company_id=stripe_company.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token(str(user.id))

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        res = client.post(
            "/connectors/stripe/dev/mock-webhook",
            json={"scenario": "payout.paid"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_connectors_dev_mock_accepts_when_enabled(db_session: Session, stripe_company: Company, monkeypatch):
    monkeypatch.setattr(settings, "stripe_dev_mock_ui_enabled", True)
    user = User(
        email="devmock2@test.dev",
        password_hash="x",
        role=Role.founder,
        company_id=stripe_company.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token(str(user.id))

    def override_db():
        yield db_session

    def fake_enqueue(webhook_pk: int):
        process_stripe_webhook_row(db_session, webhook_pk)
        return True, None

    monkeypatch.setattr(stripe_wh_inc, "enqueue_stripe_webhook_incremental_task", fake_enqueue)

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        res = client.post(
            "/connectors/stripe/dev/mock-webhook",
            json={"scenario": "refund.created"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["received"] is True
        assert data["queued"] is True
        assert db_session.query(StripeMetric).filter(StripeMetric.company_id == stripe_company.id).count() == 1
    finally:
        app.dependency_overrides.clear()


def test_connectors_dev_mock_returns_404_when_disabled(db_session: Session, stripe_company: Company, monkeypatch):
    monkeypatch.setattr(settings, "stripe_dev_mock_ui_enabled", False)
    user = User(
        email="devmock@test.dev",
        password_hash="x",
        role=Role.founder,
        company_id=stripe_company.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token(str(user.id))

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        res = client.post(
            "/connectors/stripe/dev/mock-webhook",
            json={"scenario": "payout.paid"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_connectors_dev_mock_accepts_when_enabled(db_session: Session, stripe_company: Company, monkeypatch):
    monkeypatch.setattr(settings, "stripe_dev_mock_ui_enabled", True)
    user = User(
        email="devmock2@test.dev",
        password_hash="x",
        role=Role.founder,
        company_id=stripe_company.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token(str(user.id))

    def override_db():
        yield db_session

    def fake_enqueue(webhook_pk: int):
        process_stripe_webhook_row(db_session, webhook_pk)
        return True, None

    monkeypatch.setattr(stripe_wh_inc, "enqueue_stripe_webhook_incremental_task", fake_enqueue)

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        res = client.post(
            "/connectors/stripe/dev/mock-webhook",
            json={"scenario": "refund.created"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["received"] is True
        assert data["queued"] is True
        assert db_session.query(StripeMetric).filter(StripeMetric.company_id == stripe_company.id).count() == 1
    finally:
        app.dependency_overrides.clear()
