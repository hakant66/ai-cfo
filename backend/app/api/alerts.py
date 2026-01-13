from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.metrics import AlertResponse
from app.services.metrics import compute_alerts

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/recompute", response_model=list[AlertResponse])
def recompute_alerts(db: Session = Depends(get_db)) -> list[AlertResponse]:
    alerts = compute_alerts(db, company_id=1)
    return [
        AlertResponse(
            alert_type=alert.alert_type,
            severity=alert.severity,
            message=alert.message,
            created_at=alert.created_at,
        )
        for alert in alerts
    ]
