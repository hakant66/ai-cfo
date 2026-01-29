from datetime import datetime, timezone
import pytest
from app.core import config
from app.core.wise_encryption import wise_encrypt, wise_decrypt
from app.connectors.wise.state import create_state, verify_state
from app.connectors.wise.client import WiseApiClient, WiseApiError
from app.connectors.wise.connector import WiseConnector
from app.models.models import (
    Company,
    Integration,
    IntegrationType,
    IntegrationCredentialWise,
    WiseSettings,
    WiseBalanceAccount,
    BankAccount,
    WiseTransactionRaw,
    BankTransaction,
)
from app.api.webhooks import verify_signature


def _rsa_keypair():
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return public_pem.decode("utf-8"), private_pem.decode("utf-8")


def test_oauth_state_roundtrip(monkeypatch):
    monkeypatch.setattr(config.settings, "secret_key", "test-secret")
    payload = {"company_id": 1, "user_id": 2, "environment": "sandbox", "nonce": "abc"}
    state = create_state(payload)
    parsed = verify_state(state)
    assert parsed["company_id"] == 1
    assert parsed["user_id"] == 2
    assert parsed["environment"] == "sandbox"


def test_oauth_state_tamper(monkeypatch):
    monkeypatch.setattr(config.settings, "secret_key", "test-secret")
    state = create_state({"company_id": 1})
    token, sig = state.split(".", 1)
    tampered = f"{token[::-1]}.{sig}"
    with pytest.raises(ValueError):
        verify_state(tampered)


def test_encrypt_decrypt(monkeypatch):
    public_key, private_key = _rsa_keypair()
    monkeypatch.setattr(config.settings, "wise_public_key", public_key)
    monkeypatch.setattr(config.settings, "wise_private_key", private_key)
    secret = "hello"
    encrypted = wise_encrypt(secret)
    assert wise_decrypt(encrypted) == secret


def test_refresh_token_flow(monkeypatch, db_session):
    public_key, private_key = _rsa_keypair()
    monkeypatch.setattr(config.settings, "wise_public_key", public_key)
    monkeypatch.setattr(config.settings, "wise_private_key", private_key)
    monkeypatch.setattr(config.settings, "wise_client_id", "cid")
    monkeypatch.setattr(config.settings, "wise_client_secret", "csecret")
    monkeypatch.setattr(config.settings, "wise_oauth_base_sandbox", "https://example.com")
    company = Company(name="Test Co")
    db_session.add(company)
    db_session.flush()
    integration = Integration(company_id=company.id, type=IntegrationType.wise, status="connected", credentials={})
    db_session.add(integration)
    db_session.flush()
    creds = IntegrationCredentialWise(
        company_id=company.id,
        integration_id=integration.id,
        wise_environment="sandbox",
        oauth_access_token_encrypted=wise_encrypt("old"),
        oauth_refresh_token_encrypted=wise_encrypt("refresh"),
        token_expires_at=datetime.now(timezone.utc),
        scopes=["profile"],
        sync_cursor_transactions={},
        key_version="v1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(creds)
    settings_row = WiseSettings(
        company_id=company.id,
        wise_environment="sandbox",
        wise_client_id="cid",
        wise_client_secret_encrypted=wise_encrypt("csecret"),
        webhook_secret_encrypted=None,
        key_version="v1",
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(settings_row)
    db_session.commit()

    def fake_post(url, data, timeout):
        class Response:
            status_code = 200

            def json(self):
                return {"access_token": "new", "refresh_token": "refresh2", "expires_in": 3600}
        return Response()

    monkeypatch.setattr("requests.post", fake_post)
    client = WiseApiClient(db_session, company.id, "sandbox")
    client._refresh(creds)
    assert wise_decrypt(creds.oauth_access_token_encrypted) == "new"


def test_sync_transactions_idempotent(monkeypatch, db_session):
    public_key, private_key = _rsa_keypair()
    monkeypatch.setattr(config.settings, "wise_public_key", public_key)
    monkeypatch.setattr(config.settings, "wise_private_key", private_key)
    company = Company(name="Wise Co")
    db_session.add(company)
    db_session.flush()
    integration = Integration(company_id=company.id, type=IntegrationType.wise, status="connected", credentials={})
    db_session.add(integration)
    db_session.flush()
    creds = IntegrationCredentialWise(
        company_id=company.id,
        integration_id=integration.id,
        wise_environment="sandbox",
        oauth_access_token_encrypted=wise_encrypt("token"),
        oauth_refresh_token_encrypted=wise_encrypt("refresh"),
        token_expires_at=None,
        scopes=["profile"],
        sync_cursor_transactions={},
        key_version="v1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(creds)
    account = BankAccount(
        company_id=company.id,
        name="Wise Account",
        currency="USD",
        balance=0.0,
        provider="wise",
        provider_account_id="bal-1",
    )
    db_session.add(account)
    balance_account = WiseBalanceAccount(
        company_id=company.id,
        wise_balance_account_id="bal-1",
        wise_profile_id="profile-1",
        currency="USD",
        name="Balance",
        status="active",
        details={},
        fetched_at=datetime.now(timezone.utc),
    )
    db_session.add(balance_account)
    db_session.commit()

    def fake_request(self, method, path, params=None, json=None):
        return {
            "transactions": [
                {"id": "tx-1", "date": datetime.now(timezone.utc).isoformat(), "amount": 10, "currency": "USD", "description": "Test"}
            ],
            "nextCursor": "cursor-1",
        }

    monkeypatch.setattr(WiseApiClient, "request", fake_request)
    connector = WiseConnector(db_session, company.id, "sandbox")
    connector.sync_transactions()
    connector.sync_transactions()
    assert db_session.query(WiseTransactionRaw).count() == 1
    assert db_session.query(BankTransaction).count() == 1
    db_session.refresh(creds)
    assert creds.sync_cursor_transactions["bal-1"] == "cursor-1"


def test_company_scoped_credentials(monkeypatch, db_session):
    public_key, private_key = _rsa_keypair()
    monkeypatch.setattr(config.settings, "wise_public_key", public_key)
    monkeypatch.setattr(config.settings, "wise_private_key", private_key)
    company_a = Company(name="A")
    company_b = Company(name="B")
    db_session.add_all([company_a, company_b])
    db_session.flush()
    integration_b = Integration(company_id=company_b.id, type=IntegrationType.wise, status="connected", credentials={})
    db_session.add(integration_b)
    db_session.flush()
    creds = IntegrationCredentialWise(
        company_id=company_b.id,
        integration_id=integration_b.id,
        wise_environment="sandbox",
        oauth_access_token_encrypted=wise_encrypt("token"),
        oauth_refresh_token_encrypted=wise_encrypt("refresh"),
        token_expires_at=None,
        scopes=["profile"],
        sync_cursor_transactions={},
        key_version="v1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(creds)
    db_session.commit()
    client = WiseApiClient(db_session, company_a.id, "sandbox")
    with pytest.raises(WiseApiError):
        client._credentials()


def test_webhook_signature():
    secret = "test"
    body = b'{"eventType":"balance-updated"}'
    digest = __import__("hmac").new(secret.encode("utf-8"), body, __import__("hashlib").sha256).hexdigest()
    assert verify_signature(body, digest, secret) is True
