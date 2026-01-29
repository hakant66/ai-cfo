from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.services.metrics import get_morning_brief, get_inventory_health, get_cash_forecast
from app.services.sales_quality import get_sales_quality

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/morning_brief")
def morning_brief(date: str | None = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if date:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    else:
        target_date = datetime.now(timezone.utc)
    return get_morning_brief(db, user.company_id, target_date)


@router.get("/inventory_health")
def inventory_health(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return get_inventory_health(db, user.company_id)


@router.get("/cash_forecast")
def cash_forecast(days: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return get_cash_forecast(db, user.company_id, days)


@router.get("/sales_quality")
def sales_quality(start: str, end: str, db: Session = Depends(get_db), user=Depends(require_roles(["Founder", "Finance", "Ops", "Marketing"]))):
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d").date()
        end_date = datetime.strptime(end, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid date format. Use YYYY-MM-DD.") from exc
    if end_date < start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End date must be on or after start date.")
    return get_sales_quality(db, user.company_id, start_date, end_date)
