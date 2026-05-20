import hmac
import json
import logging
from hashlib import sha256
from typing import Literal

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.models import Company, WiseWebhookReceipt, WiseWebhookSubscription, WiseSettings
from app.core.wise_encryption import wise_decrypt
from app.services.audit_log import log_event
from app.services.stripe_webhook_incremental import (
    build_synthetic_stripe_event,
    persist_stripe_webhook_event,
    should_run_incremental,
    stripe_event_to_dict,
    resolve_company_id,
)
from app.worker import wise_incremental_sync, wise_refresh_transfers


router = APIRouter(prefix="/webhooks", tags=["webhooks"])
_logger = logging.getLogger(__name__)


def _require_company(db: Session, company_id: int) -> None:
    if db.query(Company).filter(Company.id == company_id).first() is None:
        raise HTTPException(status_code=404, detail=f"Company id {company_id} not found")


def _enqueue_stripe_webhook_incremental(webhook_row_pk: int) -> tuple[bool, str | None]:
    """Queue Celery task; return (queued, error_message). Never raises — broker outages must not break HTTP."""
    try:
        from app.worker import stripe_webhook_incremental_sync as stripe_wh_task

        stripe_wh_task.delay(webhook_row_pk)
        return True, None
    except Exception as exc:
        _logger.warning("stripe_webhook_incremental_sync.delay failed: %s", exc, exc_info=True)
        return False, str(exc)


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


class StripeWebhookMockBody(BaseModel):
    company_id: int = Field(..., ge=1)
    scenario: Literal["payout.paid", "refund.created", "charge.failed"]


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    raw_body = await request.body()
    secret = (settings.stripe_webhook_secret or "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="Stripe webhooks not configured (STRIPE_WEBHOOK_SECRET).")
    try:
        event = stripe.Webhook.construct_event(raw_body, stripe_signature or "", secret, tolerance=300)
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Stripe signature: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {exc}") from exc

    event_dict = stripe_event_to_dict(event)
    company_id = resolve_company_id(db, event_dict)
    if not company_id:
        if settings.primary_company_id:
            log_event(
                db,
                settings.primary_company_id,
                "stripe.webhook.unrouted",
                "webhook",
                str(event_dict.get("id") or ""),
                None,
                {"type": event_dict.get("type")},
            )
        return {"received": True, "ignored": "no_company"}

    _require_company(db, company_id)
    row, duplicate = persist_stripe_webhook_event(db, company_id=company_id, event_dict=event_dict)
    if duplicate:
        log_event(db, company_id, "stripe.webhook.duplicate", "webhook", str(event_dict.get("id")), None, {"type": event_dict.get("type")})
        return {"received": True, "duplicate": True}

    webhook_pk = row.id
    log_event(db, company_id, "stripe.webhook.received", "webhook", str(event_dict.get("id")), None, {"type": event_dict.get("type")})

    evt_type = event_dict.get("type") or ""
    queued = False
    enqueue_error: str | None = None
    if should_run_incremental(evt_type):
        queued, enqueue_error = _enqueue_stripe_webhook_incremental(webhook_pk)
    out: dict = {"received": True, "queued": queued}
    if enqueue_error:
        out["enqueue_error"] = enqueue_error
    return out


@router.post("/stripe/mock")
async def stripe_webhook_mock(
    body: StripeWebhookMockBody,
    x_mock_stripe_secret: str | None = Header(default=None, alias="X-Mock-Stripe-Secret"),
    db: Session = Depends(get_db),
):
    try:
        expected = (settings.mock_stripe_webhook_secret or "").strip()
        if not expected or x_mock_stripe_secret != expected:
            raise HTTPException(status_code=404, detail="Not found")
        _require_company(db, body.company_id)
        event_dict = build_synthetic_stripe_event(body.scenario, body.company_id)
        row, duplicate = persist_stripe_webhook_event(db, company_id=body.company_id, event_dict=event_dict)
        if duplicate:
            return {"received": True, "duplicate": True}
        webhook_pk = row.id
        log_event(db, body.company_id, "stripe.webhook.mock", "webhook", str(event_dict.get("id")), None, {"scenario": body.scenario})
        evt_type = event_dict.get("type") or ""
        queued = False
        enqueue_error: str | None = None
        if should_run_incremental(evt_type):
            queued, enqueue_error = _enqueue_stripe_webhook_incremental(webhook_pk)
        out: dict = {
            "received": True,
            "scenario": body.scenario,
            "event_id": event_dict.get("id"),
            "queued": queued,
        }
        if enqueue_error:
            out["enqueue_error"] = enqueue_error
        return out
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("stripe_webhook_mock failed")
        raise HTTPException(status_code=500, detail=f"stripe_webhook_mock: {exc}") from exc
