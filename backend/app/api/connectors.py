from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone
from pydantic import BaseModel
import requests
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user, require_roles
from app.core.config import settings
from app.models.models import Integration, IntegrationType, StripeMetric
from app.models.models import utcnow
from app.integrations.shopify import test_connection
from app.worker import sync_shopify_data

router = APIRouter(prefix="/connectors", tags=["connectors"])


class ShopifyTestRequest(BaseModel):
    shop_domain: str
    access_token: str


class ShopifySyncRequest(BaseModel):
    shop_domain: str
    access_token: str


class ShopifySettingsRequest(BaseModel):
    shop_domain: str
    access_token: str


class StripeSettingsRequest(BaseModel):
    stripe_account: str | None = None
    publishable_key: str | None = None
    secret_key: str | None = None


class StripeDateRangeRequest(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    limit: int | None = None


@router.post("/shopify/test")
def shopify_test(payload: ShopifyTestRequest, user=Depends(get_current_user)):
    result = test_connection(payload.shop_domain, payload.access_token)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.post("/shopify/sync")
def shopify_sync(
    payload: ShopifySyncRequest | None = None,
    shop_domain: str | None = None,
    access_token: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["Founder"])),
):
    if payload:
        shop_domain = payload.shop_domain
        access_token = payload.access_token
    if not shop_domain or not access_token:
        raise HTTPException(status_code=400, detail="shop_domain and access_token required")
    integration = db.query(Integration).filter(
        Integration.company_id == user.company_id,
        Integration.type == IntegrationType.shopify,
    ).first()
    if not integration:
        integration = Integration(
            company_id=user.company_id,
            type=IntegrationType.shopify,
            status="connected",
            credentials={"shop_domain": shop_domain, "access_token": access_token},
        )
        db.add(integration)
    else:
        integration.credentials = {"shop_domain": shop_domain, "access_token": access_token}
        integration.status = "connected"
    db.commit()
    sync_shopify_data.delay(user.company_id)
    return {"status": "queued"}


@router.post("/shopify/settings")
def shopify_settings(
    payload: ShopifySettingsRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["Founder"])),
):
    integration = db.query(Integration).filter(
        Integration.company_id == user.company_id,
        Integration.type == IntegrationType.shopify,
    ).first()
    if not integration:
        integration = Integration(
            company_id=user.company_id,
            type=IntegrationType.shopify,
            status="connected",
            credentials={"shop_domain": payload.shop_domain, "access_token": payload.access_token},
        )
        db.add(integration)
    else:
        integration.credentials = {"shop_domain": payload.shop_domain, "access_token": payload.access_token}
        integration.status = "connected"
    db.commit()
    return {"status": "saved"}


@router.post("/stripe/sync-revenue")
def stripe_sync_revenue(
    db: Session = Depends(get_db),
    user=Depends(require_roles(["Founder", "Finance"])),
):
    integration = db.query(Integration).filter(
        Integration.company_id == user.company_id,
        Integration.type == IntegrationType.stripe,
    ).first()
    credentials = integration.credentials if integration else {}

    try:
        response = requests.post(
            f"{settings.stripe_api_base.rstrip('/')}/sync/revenue",
            json={
                "stripe_account": credentials.get("stripe_account"),
                "publishable_key": credentials.get("publishable_key"),
                "secret_key": credentials.get("secret_key"),
            },
            timeout=60,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        detail = getattr(exc.response, "text", "") if getattr(exc, "response", None) else str(exc)
        raise HTTPException(status_code=502, detail=f"Stripe sync failed: {detail}") from exc

    integration = db.query(Integration).filter(
        Integration.company_id == user.company_id,
        Integration.type == IntegrationType.stripe,
    ).first()
    if not integration:
        integration = Integration(
            company_id=user.company_id,
            type=IntegrationType.stripe,
            status="connected",
            credentials={},
            last_sync_at=utcnow(),
        )
        db.add(integration)
    else:
        integration.status = "connected"
        integration.last_sync_at = utcnow()
    db.commit()

    return response.json()


@router.get("/stripe/settings")
def stripe_settings(
    db: Session = Depends(get_db),
    user=Depends(require_roles(["Founder", "Finance"])),
):
    integration = db.query(Integration).filter(
        Integration.company_id == user.company_id,
        Integration.type == IntegrationType.stripe,
    ).first()
    credentials = integration.credentials if integration else {}
    return {
        "stripe_account": credentials.get("stripe_account"),
        "has_publishable_key": bool(credentials.get("publishable_key")),
        "has_secret_key": bool(credentials.get("secret_key")),
    }


@router.post("/stripe/settings")
def stripe_save_settings(
    payload: StripeSettingsRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["Founder", "Finance"])),
):
    integration = db.query(Integration).filter(
        Integration.company_id == user.company_id,
        Integration.type == IntegrationType.stripe,
    ).first()
    credentials = integration.credentials if integration else {}
    if payload.stripe_account is not None:
        credentials["stripe_account"] = payload.stripe_account
    if payload.publishable_key is not None:
        credentials["publishable_key"] = payload.publishable_key
    if payload.secret_key is not None:
        credentials["secret_key"] = payload.secret_key

    if not integration:
        integration = Integration(
            company_id=user.company_id,
            type=IntegrationType.stripe,
            status="connected" if payload.secret_key else "disconnected",
            credentials=credentials,
            last_sync_at=utcnow(),
        )
        db.add(integration)
    else:
        integration.credentials = credentials
        integration.status = "connected" if credentials.get("secret_key") else integration.status
        integration.last_sync_at = utcnow()
    db.commit()

    return {
        "stripe_account": credentials.get("stripe_account"),
        "has_publishable_key": bool(credentials.get("publishable_key")),
        "has_secret_key": bool(credentials.get("secret_key")),
    }


@router.post("/stripe/balance-payouts")
def stripe_balance_payouts(
    payload: StripeDateRangeRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["Founder", "Finance"])),
):
    integration = db.query(Integration).filter(
        Integration.company_id == user.company_id,
        Integration.type == IntegrationType.stripe,
    ).first()
    credentials = integration.credentials if integration else {}

    try:
        response = requests.post(
            f"{settings.stripe_api_base.rstrip('/')}/sync/balance-payouts",
            json={
                "stripe_account": credentials.get("stripe_account"),
                "publishable_key": credentials.get("publishable_key"),
                "secret_key": credentials.get("secret_key"),
                "start_date": payload.start_date,
                "end_date": payload.end_date,
            },
            timeout=60,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        detail = getattr(exc.response, "text", "") if getattr(exc, "response", None) else str(exc)
        raise HTTPException(status_code=502, detail=f"Stripe balance sync failed: {detail}") from exc

    if integration:
        integration.last_sync_at = utcnow()
        db.commit()

    return response.json()


@router.post("/stripe/metrics/true-net-margin")
def stripe_true_net_margin(
    payload: StripeDateRangeRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["Founder", "Finance"])),
):
    integration = db.query(Integration).filter(
        Integration.company_id == user.company_id,
        Integration.type == IntegrationType.stripe,
    ).first()
    credentials = integration.credentials if integration else {}

    try:
        response = requests.post(
            f"{settings.stripe_api_base.rstrip('/')}/metrics/true-net-margin",
            json={
                "stripe_account": credentials.get("stripe_account"),
                "publishable_key": credentials.get("publishable_key"),
                "secret_key": credentials.get("secret_key"),
                "start_date": payload.start_date,
                "end_date": payload.end_date,
                "limit": payload.limit,
            },
            timeout=60,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        detail = getattr(exc.response, "text", "") if getattr(exc, "response", None) else str(exc)
        raise HTTPException(status_code=502, detail=f"Stripe metrics sync failed: {detail}") from exc

    if integration:
        integration.last_sync_at = utcnow()
        db.commit()

    return response.json()


@router.post("/stripe/metrics/true-net-margin/store")
def stripe_store_true_net_margin(
    payload: StripeDateRangeRequest,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["Founder", "Finance"])),
):
    integration = db.query(Integration).filter(
        Integration.company_id == user.company_id,
        Integration.type == IntegrationType.stripe,
    ).first()
    credentials = integration.credentials if integration else {}

    try:
        response = requests.post(
            f"{settings.stripe_api_base.rstrip('/')}/metrics/true-net-margin",
            json={
                "stripe_account": credentials.get("stripe_account"),
                "publishable_key": credentials.get("publishable_key"),
                "secret_key": credentials.get("secret_key"),
                "start_date": payload.start_date,
                "end_date": payload.end_date,
                "limit": payload.limit,
            },
            timeout=60,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        detail = getattr(exc.response, "text", "") if getattr(exc, "response", None) else str(exc)
        raise HTTPException(status_code=502, detail=f"Stripe metrics sync failed: {detail}") from exc

    payload_json = response.json()
    items = payload_json.get("items", [])
    metric_rows = [
        StripeMetric(
            company_id=user.company_id,
            metric_type="true_net_margin",
            payload=item,
            created_at=utcnow(),
        )
        for item in items
    ]
    if metric_rows:
        db.bulk_save_objects(metric_rows)
    if integration:
        integration.last_sync_at = utcnow()
    db.commit()

    return {"stored": len(metric_rows), "count": len(items)}


@router.get("/stripe/metrics/true-net-margin")
def list_true_net_margin(
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["Founder", "Finance"])),
):
    query = db.query(StripeMetric).filter(
        StripeMetric.company_id == user.company_id,
        StripeMetric.metric_type == "true_net_margin",
    )
    if start_date:
        query = query.filter(StripeMetric.created_at >= datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc))
    if end_date:
        query = query.filter(StripeMetric.created_at <= datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc))
    rows = query.order_by(StripeMetric.created_at.desc()).limit(limit).all()
    return {"items": [row.payload for row in rows], "count": len(rows)}


@router.delete("/stripe/metrics/true-net-margin")
def clear_true_net_margin(
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_roles(["Founder", "Finance"])),
):
    query = db.query(StripeMetric).filter(
        StripeMetric.company_id == user.company_id,
        StripeMetric.metric_type == "true_net_margin",
    )
    if start_date:
        query = query.filter(StripeMetric.created_at >= datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc))
    if end_date:
        query = query.filter(StripeMetric.created_at <= datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc))
    deleted = query.delete(synchronize_session=False)
    db.commit()
    return {"deleted": deleted}
