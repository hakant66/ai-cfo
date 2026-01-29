from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_user, require_roles
from app.connectors.wise.client import exchange_oauth_code, WiseApiError
from app.connectors.wise.config import oauth_base_url
from app.connectors.wise.state import create_state, verify_state
from app.core.wise_encryption import wise_encrypt, wise_decrypt
from app.models.models import Integration, IntegrationType, IntegrationCredentialWise, WiseSettings
from app.schemas.wise import WiseSettingsOut, WiseSettingsUpdate
from app.services.audit_log import log_event
from app.worker import wise_full_sync
import uuid


router = APIRouter(prefix="/connectors/wise", tags=["wise"])


@router.get("/oauth/start")
def oauth_start(
    environment: str = Query("sandbox", pattern="^(sandbox|production)$"),
    return_url: str | None = None,
    include_write: bool = False,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["Founder", "Finance"])),
):
    if include_write and not settings.wise_write_enabled:
        raise HTTPException(status_code=400, detail="Write scopes are disabled")
    stored = db.query(WiseSettings).filter(
        WiseSettings.company_id == user.company_id,
        WiseSettings.wise_environment == environment,
    ).first()
    auth_mode = "oauth"
    if stored and stored.wise_api_token_encrypted:
        auth_mode = "api_token"
    if auth_mode == "api_token":
        raise HTTPException(status_code=400, detail="OAuth disabled when API token is configured")
    client_id = stored.wise_client_id if stored and stored.wise_client_id else settings.wise_client_id
    client_secret_value = None
    if stored and stored.wise_client_secret_encrypted:
        client_secret_value = wise_decrypt(stored.wise_client_secret_encrypted)
    elif settings.wise_client_secret:
        client_secret_value = settings.wise_client_secret
    if not client_id or not client_secret_value:
        raise HTTPException(status_code=500, detail="Wise OAuth client not configured")
    scopes = settings.wise_oauth_scopes_read
    if include_write and settings.wise_oauth_scopes_write:
        scopes = f"{scopes} {settings.wise_oauth_scopes_write}".strip()
    state = create_state(
        {
            "company_id": user.company_id,
            "user_id": user.id,
            "environment": environment,
            "nonce": str(uuid.uuid4()),
            "return_url": return_url,
        }
    )
    redirect_uri = settings.wise_redirect_uri
    if not redirect_uri:
        raise HTTPException(status_code=500, detail="WISE_REDIRECT_URI not configured")
    auth_url = (
        f"{oauth_base_url(environment)}/oauth/authorize"
        f"?response_type=code&client_id={client_id}"
        f"&redirect_uri={redirect_uri}&scope={scopes}&state={state}"
    )
    return RedirectResponse(auth_url)


@router.get("/oauth/callback")
def oauth_callback(code: str, state: str, db: Session = Depends(get_db)):
    try:
        payload = verify_state(state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    company_id = int(payload.get("company_id") or 0)
    environment = payload.get("environment") or "sandbox"
    if not company_id:
        raise HTTPException(status_code=400, detail="Invalid state payload")
    stored = db.query(WiseSettings).filter(
        WiseSettings.company_id == company_id,
        WiseSettings.wise_environment == environment,
    ).first()
    if stored and stored.wise_api_token_encrypted:
        raise HTTPException(status_code=400, detail="OAuth disabled when API token is configured")
    client_id = stored.wise_client_id if stored and stored.wise_client_id else settings.wise_client_id
    client_secret_value = None
    if stored and stored.wise_client_secret_encrypted:
        client_secret_value = wise_decrypt(stored.wise_client_secret_encrypted)
    elif settings.wise_client_secret:
        client_secret_value = settings.wise_client_secret
    if not client_id or not client_secret_value:
        raise HTTPException(status_code=500, detail="Wise OAuth client not configured")
    try:
        token_payload = exchange_oauth_code(environment, code, settings.wise_redirect_uri, client_id, client_secret_value)
    except WiseApiError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    integration = db.query(Integration).filter(
        Integration.company_id == company_id,
        Integration.type == IntegrationType.wise,
    ).first()
    if not integration:
        integration = Integration(
            company_id=company_id,
            type=IntegrationType.wise,
            status="connected",
            credentials={},
            last_sync_at=None,
        )
        db.add(integration)
        db.flush()
    else:
        integration.status = "connected"
    expires_in = int(token_payload.get("expires_in") or 0)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in) if expires_in else None
    creds = db.query(IntegrationCredentialWise).filter(
        IntegrationCredentialWise.company_id == company_id,
        IntegrationCredentialWise.wise_environment == environment,
    ).first()
    if not creds:
        creds = IntegrationCredentialWise(
            company_id=company_id,
            integration_id=integration.id,
            wise_environment=environment,
            oauth_access_token_encrypted=wise_encrypt(token_payload["access_token"]),
            oauth_refresh_token_encrypted=wise_encrypt(token_payload["refresh_token"]),
            token_expires_at=expires_at,
            scopes=(token_payload.get("scope") or "").split(),
            last_sync_at=None,
            sync_cursor_transactions={},
            key_version="v1",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(creds)
    else:
        creds.oauth_access_token_encrypted = wise_encrypt(token_payload["access_token"])
        creds.oauth_refresh_token_encrypted = wise_encrypt(token_payload["refresh_token"])
        creds.token_expires_at = expires_at
        creds.scopes = (token_payload.get("scope") or "").split()
        creds.updated_at = datetime.now(timezone.utc)
    db.commit()
    log_event(db, company_id, "wise.oauth.connected", "integration", str(integration.id), payload.get("user_id"), {"environment": environment})
    return {"status": "connected"}


@router.post("/disconnect")
def disconnect(environment: str = Query("sandbox", pattern="^(sandbox|production)$"), db: Session = Depends(get_db), user=Depends(require_roles(["Founder", "Finance"]))):
    integration = db.query(Integration).filter(
        Integration.company_id == user.company_id,
        Integration.type == IntegrationType.wise,
    ).first()
    creds = db.query(IntegrationCredentialWise).filter(
        IntegrationCredentialWise.company_id == user.company_id,
        IntegrationCredentialWise.wise_environment == environment,
    ).all()
    for item in creds:
        db.delete(item)
    if integration:
        remaining = db.query(IntegrationCredentialWise).filter(
            IntegrationCredentialWise.company_id == user.company_id
        ).count()
        if remaining == 0:
            integration.status = "disconnected"
    db.commit()
    log_event(db, user.company_id, "wise.oauth.disconnected", "integration", str(integration.id) if integration else None, user.id, {"environment": environment})
    return {"status": "disconnected"}


@router.get("/status")
def status(environment: str = Query("sandbox", pattern="^(sandbox|production)$"), db: Session = Depends(get_db), user=Depends(get_current_user)):
    integration = db.query(Integration).filter(
        Integration.company_id == user.company_id,
        Integration.type == IntegrationType.wise,
    ).first()
    stored = db.query(WiseSettings).filter(
        WiseSettings.company_id == user.company_id,
        WiseSettings.wise_environment == environment,
    ).first()
    creds = db.query(IntegrationCredentialWise).filter(
        IntegrationCredentialWise.company_id == user.company_id,
        IntegrationCredentialWise.wise_environment == environment,
    ).first()
    has_api_token = bool(stored and stored.wise_api_token_encrypted) or bool(settings.wise_api_token)
    return {
        "connected": integration is not None and integration.status == "connected" and creds is not None,
        "environment": environment,
        "last_sync_at": creds.last_sync_at.isoformat() if creds and creds.last_sync_at else None,
        "token_expires_at": creds.token_expires_at.isoformat() if creds and creds.token_expires_at else None,
        "has_client_secret": bool(stored and stored.wise_client_secret_encrypted),
        "has_webhook_secret": bool(stored and stored.webhook_secret_encrypted),
        "has_api_token": has_api_token,
    }


@router.post("/sync")
def sync(environment: str = Query("sandbox", pattern="^(sandbox|production)$"), db: Session = Depends(get_db), user=Depends(require_roles(["Founder", "Finance"]))):
    wise_full_sync.delay(user.company_id, environment)
    log_event(db, user.company_id, "wise.sync.triggered", "integration", str(user.company_id), user.id, {"environment": environment})
    return {"status": "queued"}


@router.get("/settings", response_model=WiseSettingsOut)
def get_settings(environment: str = Query("sandbox", pattern="^(sandbox|production)$"), db: Session = Depends(get_db), user=Depends(require_roles(["Founder"]))):
    stored = db.query(WiseSettings).filter(
        WiseSettings.company_id == user.company_id,
        WiseSettings.wise_environment == environment,
    ).first()
    if not stored:
        return WiseSettingsOut(
            wise_client_id=None,
            wise_environment="sandbox",
            has_client_secret=False,
            has_webhook_secret=False,
            has_api_token=bool(settings.wise_api_token),
        )
    return WiseSettingsOut(
        wise_client_id=stored.wise_client_id,
        wise_environment=stored.wise_environment,
        has_client_secret=bool(stored.wise_client_secret_encrypted),
        has_webhook_secret=bool(stored.webhook_secret_encrypted),
        has_api_token=bool(stored.wise_api_token_encrypted) or bool(settings.wise_api_token),
    )


@router.patch("/settings", response_model=WiseSettingsOut)
def update_settings(payload: WiseSettingsUpdate, db: Session = Depends(get_db), user=Depends(require_roles(["Founder"]))):
    environment = payload.wise_environment or "sandbox"
    stored = db.query(WiseSettings).filter(
        WiseSettings.company_id == user.company_id,
        WiseSettings.wise_environment == environment,
    ).first()
    if not stored:
        stored = WiseSettings(company_id=user.company_id, wise_environment=environment)
        db.add(stored)
    if payload.wise_client_id is not None:
        stored.wise_client_id = payload.wise_client_id
    if payload.auth_mode == "api_token":
        stored.wise_client_id = None
        stored.wise_client_secret_encrypted = None
    if payload.wise_client_secret and payload.auth_mode != "api_token":
        stored.wise_client_secret_encrypted = wise_encrypt(payload.wise_client_secret)
    if payload.webhook_secret:
        stored.webhook_secret_encrypted = wise_encrypt(payload.webhook_secret)
    if payload.wise_api_token:
        stored.wise_api_token_encrypted = wise_encrypt(payload.wise_api_token)
    if payload.auth_mode == "api_token" and not payload.wise_api_token and not stored.wise_api_token_encrypted and settings.wise_api_token:
        stored.wise_api_token_encrypted = wise_encrypt(settings.wise_api_token)
    if payload.wise_environment:
        stored.wise_environment = payload.wise_environment
    stored.updated_at = datetime.now(timezone.utc)
    db.commit()
    return WiseSettingsOut(
        wise_client_id=stored.wise_client_id,
        wise_environment=stored.wise_environment,
        has_client_secret=bool(stored.wise_client_secret_encrypted),
        has_webhook_secret=bool(stored.webhook_secret_encrypted),
        has_api_token=bool(stored.wise_api_token_encrypted),
    )


@router.get("/test")
def test_connection(environment: str = Query("sandbox", pattern="^(sandbox|production)$"), db: Session = Depends(get_db), user=Depends(require_roles(["Founder", "Finance"]))):
    stored = db.query(WiseSettings).filter(
        WiseSettings.company_id == user.company_id,
        WiseSettings.wise_environment == environment,
    ).first()
    if not stored or not stored.wise_client_id or not stored.wise_client_secret_encrypted:
        raise HTTPException(status_code=400, detail="Wise settings not configured for environment")
    creds = db.query(IntegrationCredentialWise).filter(
        IntegrationCredentialWise.company_id == user.company_id,
        IntegrationCredentialWise.wise_environment == environment,
    ).first()
    if not creds:
        return {"ok": False, "message": "Not connected. Complete OAuth flow first."}
    try:
        from app.connectors.wise.client import WiseApiClient
        from app.connectors.wise.config import WiseEndpoints
        client = WiseApiClient(db, user.company_id, environment)
        endpoints = WiseEndpoints()
        client.request("GET", endpoints.profiles)
        return {"ok": True, "message": "Connection successful."}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
