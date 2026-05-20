"""Stripe webhook ingestion: company routing, idempotent receipts, incremental True Net Margin merge."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Integration, IntegrationType, StripeMetric, StripeWebhookEvent, utcnow


INCREMENTAL_DAYS = 3

INCREMENTAL_PREFIXES = (
    "balance.",
    "payout.",
    "charge.",
    "refund.",
)


def should_run_incremental(event_type: str) -> bool:
    if not event_type:
        return False
    return any(event_type.startswith(p) for p in INCREMENTAL_PREFIXES)


def stripe_event_to_dict(event: Any) -> dict:
    if isinstance(event, dict):
        return event
    to_dict = getattr(event, "to_dict", None)
    if callable(to_dict):
        return to_dict()
    return json.loads(json.dumps(event, default=str))


def resolve_company_id(db: Session, event: dict) -> int | None:
    acct = event.get("account")
    if acct:
        integrations = db.query(Integration).filter(Integration.type == IntegrationType.stripe).all()
        for ing in integrations:
            creds = ing.credentials or {}
            if creds.get("stripe_account") == acct:
                return ing.company_id
    obj = (event.get("data") or {}).get("object") or {}
    md = obj.get("metadata") or {}
    raw_cid = md.get("aicfo_company_id")
    if raw_cid is not None:
        try:
            return int(raw_cid)
        except (TypeError, ValueError):
            pass
    return settings.stripe_webhook_default_company_id


def _existing_true_net_margin_ids(db: Session, company_id: int) -> set[str]:
    rows = (
        db.query(StripeMetric)
        .filter(
            StripeMetric.company_id == company_id,
            StripeMetric.metric_type == "true_net_margin",
        )
        .all()
    )
    out: set[str] = set()
    for row in rows:
        payload = row.payload
        if isinstance(payload, dict):
            bid = payload.get("id")
            if isinstance(bid, str):
                out.add(bid)
    return out


def merge_true_net_margin_dedupe(db: Session, company_id: int, items: list[dict]) -> int:
    if not items:
        return 0
    existing = _existing_true_net_margin_ids(db, company_id)
    inserted = 0
    now = utcnow()
    for item in items:
        bid = item.get("id")
        if not bid or bid in existing:
            continue
        existing.add(bid)
        db.add(
            StripeMetric(
                company_id=company_id,
                metric_type="true_net_margin",
                payload=item,
                created_at=now,
            )
        )
        inserted += 1
    return inserted


def pull_incremental_from_stripe_api(db: Session, company_id: int) -> dict:
    integration = (
        db.query(Integration)
        .filter(
            Integration.company_id == company_id,
            Integration.type == IntegrationType.stripe,
        )
        .first()
    )
    credentials = integration.credentials if integration else {}
    secret_key = credentials.get("secret_key")
    if not secret_key:
        return {"skipped": "no_secret_key", "inserted": 0}

    end_d = datetime.now(timezone.utc).date()
    start_d = end_d - timedelta(days=INCREMENTAL_DAYS)
    url = f"{settings.stripe_api_base.rstrip('/')}/metrics/true-net-margin"
    response = requests.post(
        url,
        json={
            "stripe_account": credentials.get("stripe_account"),
            "publishable_key": credentials.get("publishable_key"),
            "secret_key": secret_key,
            "start_date": start_d.isoformat(),
            "end_date": end_d.isoformat(),
            "limit": 100,
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    items = payload.get("items") or []
    inserted = merge_true_net_margin_dedupe(db, company_id, items)
    if integration:
        integration.last_sync_at = utcnow()
    return {"inserted": inserted, "fetched": len(items)}


def synthetic_true_net_margin_line(event: dict) -> dict:
    evt_id = event.get("id") or f"evt_mock_{uuid.uuid4().hex[:16]}"
    event_type = event.get("type") or "unknown"
    obj = (event.get("data") or {}).get("object") or {}
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    currency = (obj.get("currency") or "usd").upper()
    syn_id = f"syn_webhook_{evt_id}"

    if event_type == "payout.paid":
        amount_cents = int(obj.get("amount") or 0)
        gross = amount_cents / 100.0
        return {
            "id": syn_id,
            "type": "payout",
            "date": now_iso,
            "gross_amount": gross,
            "stripe_fee": 0.0,
            "net_amount": gross,
            "margin_pct": 100.0 if gross > 0 else 0.0,
            "currency": currency,
            "available_on": now_iso,
            "payment_intent_amount": None,
            "tax_amount": None,
            "customer_metadata": {"synthetic": True, "webhook": event_type, "payout_id": obj.get("id")},
            "source_id": obj.get("id"),
        }

    if event_type == "refund.created":
        amount_cents = int(obj.get("amount") or 2500)
        gross = -(abs(amount_cents) / 100.0)
        fee = 0.35
        net = gross + fee
        return {
            "id": syn_id,
            "type": "refund",
            "date": now_iso,
            "gross_amount": gross,
            "stripe_fee": fee,
            "net_amount": net,
            "margin_pct": round((net / gross) * 100, 2) if gross != 0 else 0.0,
            "currency": currency,
            "available_on": now_iso,
            "payment_intent_amount": None,
            "tax_amount": None,
            "customer_metadata": {"synthetic": True, "webhook": event_type, "refund_id": obj.get("id")},
            "source_id": obj.get("id"),
        }

    if event_type == "charge.failed":
        amount_cents = int(obj.get("amount") or 5000)
        gross = amount_cents / 100.0
        fee = 0.0
        net = 0.0
        return {
            "id": syn_id,
            "type": "charge",
            "date": now_iso,
            "gross_amount": gross,
            "stripe_fee": fee,
            "net_amount": net,
            "margin_pct": 0.0,
            "currency": currency,
            "available_on": now_iso,
            "payment_intent_amount": gross,
            "tax_amount": None,
            "customer_metadata": {
                "synthetic": True,
                "webhook": event_type,
                "failure_code": obj.get("failure_code") or "card_declined",
                "charge_id": obj.get("id"),
            },
            "source_id": obj.get("id"),
        }

    return {
        "id": syn_id,
        "type": event_type,
        "date": now_iso,
        "gross_amount": 0.0,
        "stripe_fee": 0.0,
        "net_amount": 0.0,
        "margin_pct": 0.0,
        "currency": currency,
        "available_on": None,
        "payment_intent_amount": None,
        "tax_amount": None,
        "customer_metadata": {"synthetic": True, "webhook": event_type},
        "source_id": obj.get("id"),
    }


def is_synthetic_event(event: dict) -> bool:
    if event.get("_aicfo_synthetic") is True:
        return True
    eid = event.get("id")
    return isinstance(eid, str) and eid.startswith("evt_mock_")


def process_stripe_webhook_row(db: Session, stripe_webhook_event_pk: int) -> dict:
    row = db.query(StripeWebhookEvent).filter(StripeWebhookEvent.id == stripe_webhook_event_pk).first()
    if not row:
        return {"error": "missing_row"}
    event = row.payload if isinstance(row.payload, dict) else {}
    try:
        if is_synthetic_event(event):
            line = synthetic_true_net_margin_line(event)
            inserted = merge_true_net_margin_dedupe(db, row.company_id, [line])
            out: dict = {"mode": "synthetic", "inserted": inserted}
        else:
            out = pull_incremental_from_stripe_api(db, row.company_id)
            out["mode"] = "api"
    except Exception:
        db.rollback()
        raise
    row.processed_at = utcnow()
    db.add(row)
    db.commit()
    return out


def persist_stripe_webhook_event(
    db: Session,
    *,
    company_id: int,
    event_dict: dict,
) -> tuple[StripeWebhookEvent | None, bool]:
    """Insert webhook row. Returns (row, duplicate) where duplicate means event id already processed."""
    stripe_event_id = event_dict.get("id")
    if not stripe_event_id:
        raise ValueError("Stripe event missing id")
    event_type = event_dict.get("type") or "unknown"
    account_id = event_dict.get("account")
    livemode = bool(event_dict.get("livemode", True))
    row = StripeWebhookEvent(
        stripe_event_id=str(stripe_event_id),
        company_id=company_id,
        event_type=str(event_type),
        account_id=str(account_id) if account_id else None,
        livemode=livemode,
        payload=event_dict,
        created_at=utcnow(),
    )
    db.add(row)
    try:
        db.flush()
        db.commit()
        db.refresh(row)
        return row, False
    except IntegrityError as exc:
        db.rollback()
        # Unique violation on stripe_event_id → idempotent replay (Stripe or retried mock).
        # Other integrity errors (e.g. missing company_id FK) must not be masked as duplicate.
        orig = getattr(exc, "orig", None)
        pgcode = getattr(orig, "pgcode", None) if orig is not None else None
        if pgcode == "23505":
            return None, True
        err_txt = str(orig or exc).lower()
        if "unique" in err_txt:
            return None, True
        raise


def build_synthetic_stripe_event(scenario: str, company_id: int) -> dict:
    uid = uuid.uuid4().hex[:12]
    now_ts = int(datetime.now(timezone.utc).timestamp())
    meta = {"aicfo_company_id": str(company_id)}

    if scenario == "payout.paid":
        return {
            "id": f"evt_mock_payout_paid_{uid}",
            "object": "event",
            "api_version": "2024-06-20",
            "created": now_ts,
            "livemode": False,
            "type": "payout.paid",
            "pending_webhooks": 0,
            "_aicfo_synthetic": True,
            "data": {
                "object": {
                    "id": f"po_mock_{uid}",
                    "object": "payout",
                    "amount": 12550,
                    "currency": "usd",
                    "status": "paid",
                    "arrival_date": now_ts,
                    "created": now_ts,
                    "metadata": meta,
                }
            },
        }

    if scenario == "refund.created":
        return {
            "id": f"evt_mock_refund_created_{uid}",
            "object": "event",
            "api_version": "2024-06-20",
            "created": now_ts,
            "livemode": False,
            "type": "refund.created",
            "pending_webhooks": 0,
            "_aicfo_synthetic": True,
            "data": {
                "object": {
                    "id": f"re_mock_{uid}",
                    "object": "refund",
                    "amount": 2500,
                    "currency": "usd",
                    "status": "succeeded",
                    "created": now_ts,
                    "metadata": meta,
                }
            },
        }

    if scenario == "charge.failed":
        return {
            "id": f"evt_mock_charge_failed_{uid}",
            "object": "event",
            "api_version": "2024-06-20",
            "created": now_ts,
            "livemode": False,
            "type": "charge.failed",
            "pending_webhooks": 0,
            "_aicfo_synthetic": True,
            "data": {
                "object": {
                    "id": f"ch_mock_{uid}",
                    "object": "charge",
                    "amount": 5000,
                    "currency": "usd",
                    "status": "failed",
                    "failure_code": "card_declined",
                    "created": now_ts,
                    "metadata": meta,
                }
            },
        }

    raise ValueError(f"Unknown synthetic scenario: {scenario}")
