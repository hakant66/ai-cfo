from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.services.alerts import recompute_alerts

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/recompute")
def recompute(db: Session = Depends(get_db), user=Depends(get_current_user)):
    alerts = recompute_alerts(db, user.company_id)
    return {"count": len(alerts)}