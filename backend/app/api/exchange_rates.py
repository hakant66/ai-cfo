from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.services.exchange_rates import list_exchange_rates, refresh_exchange_rates, update_exchange_rate

router = APIRouter(prefix="/exchange-rates", tags=["exchange-rates"])


@router.get("")
def get_exchange_rates(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return {"items": list_exchange_rates(db, user.company_id)}


@router.post("/refresh")
def refresh_rates(db: Session = Depends(get_db), user=Depends(require_roles(["Founder", "Finance"]))):
    try:
        return refresh_exchange_rates(db, user.company_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to refresh exchange rates: {exc}",
        ) from exc


@router.patch("/{pair}")
def update_rate(pair: str, payload: dict, db: Session = Depends(get_db), user=Depends(require_roles(["Founder", "Finance"]))):
    rate = payload.get("rate")
    if rate is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rate is required")
    try:
        rate_value = float(rate)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rate must be a number") from exc
    return update_exchange_rate(db, user.company_id, pair, rate_value)
