import hmac
import json
from hashlib import sha256
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.models import WiseWebhookReceipt, WiseWebhookSubscription, WiseSettings
from app.core.wise_encryption import wise_decrypt
from app.services.audit_log import log_event
from app.worker import wise_incremental_sync, wise_refresh_transfers


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def verify_signature(raw_body: bytes, signature: str | None, secret: str) -> bool:
    if not signature or not secret:
        return False
    digest = hmac.new(secret.encode("utf-8"), raw_body, sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


@router.post("/wise")
async def wise_webhook(
    request: Request,
    x_signature: str | None = Header(default=None, alias="X-Signature"),
    db: Session = Depends(get_db),
):
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        payload = {}
    subscription_id = str(payload.get("subscriptionId") or payload.get("subscription_id") or "")
    event_type = payload.get("eventType") or payload.get("event_type") or "unknown"
    subscription = None
    if subscription_id:
        subscription = db.query(WiseWebhookSubscription).filter(
            WiseWebhookSubscription.wise_subscription_id == subscription_id
        ).first()
    company_id = subscription.company_id if subscription else settings.primary_company_id
    if not company_id:
        raise HTTPException(status_code=400, detail="Webhook not routed")
    secret = subscription.secret_ref if subscription and subscription.secret_ref else None
    if not secret:
        env = subscription.wise_environment if subscription and subscription.wise_environment else "sandbox"
        stored = db.query(WiseSettings).filter(
            WiseSettings.company_id == company_id,
            WiseSettings.wise_environment == env,
        ).first()
        if stored and stored.webhook_secret_encrypted:
            secret = wise_decrypt(stored.webhook_secret_encrypted)
    if not secret:
        secret = settings.wise_webhook_secret
    if not verify_signature(raw_body, x_signature, secret):
        receipt = WiseWebhookReceipt(
            company_id=company_id,
            wise_subscription_id=subscription_id or None,
            event_type=event_type,
            status="rejected",
            reason="signature_mismatch",
            raw=payload,
        )
        db.add(receipt)
        db.commit()
        log_event(db, company_id, "wise.webhook.rejected", "webhook", subscription_id or "unknown", None, {"event_type": event_type})
        raise HTTPException(status_code=401, detail="Invalid signature")
    receipt = WiseWebhookReceipt(
        company_id=company_id,
        wise_subscription_id=subscription_id or None,
        event_type=event_type,
        status="received",
        raw=payload,
    )
    db.add(receipt)
    db.commit()
    if "transfer" in str(event_type).lower():
        wise_refresh_transfers.delay(company_id, subscription.wise_subscription_id if subscription else None)
    else:
        wise_incremental_sync.delay(company_id, subscription.wise_subscription_id if subscription else None)
    log_event(db, company_id, "wise.webhook.received", "webhook", subscription_id or "unknown", None, {"event_type": event_type})
    return {"status": "ok"}
