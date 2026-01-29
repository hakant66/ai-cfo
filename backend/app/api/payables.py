from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import Bill

router = APIRouter(prefix="/payables", tags=["payables"])


@router.get("")
def list_payables(db: Session = Depends(get_db), user=Depends(get_current_user)):
    bills = db.query(Bill).filter(Bill.company_id == user.company_id).order_by(Bill.due_date.asc()).all()
    return [
        {
            "id": bill.id,
            "vendor": bill.vendor,
            "amount": bill.amount,
            "due_date": bill.due_date.isoformat(),
            "status": bill.status,
            "criticality": bill.criticality,
            "recommended_payment_date": bill.due_date.isoformat(),
        }
        for bill in bills
    ]