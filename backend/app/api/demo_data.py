from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.services.demo_data import clear_company_demo_data, reseed_company_demo_data
from app.worker import sync_shopify_data

router = APIRouter(prefix="/demo-data", tags=["demo-data"])


@router.post("/seed")
def seed_demo_data(db: Session = Depends(get_db), user=Depends(require_roles(["Founder"]))):
    company = reseed_company_demo_data(db, user.company_id)
    sync_shopify_data.delay(company.id)
    return {"status": "queued", "company_id": company.id, "company_name": company.name}


@router.delete("/clear")
def clear_demo_data(db: Session = Depends(get_db), user=Depends(require_roles(["Founder"]))):
    company = clear_company_demo_data(db, user.company_id)
    return {"status": "cleared", "company_id": company.id, "company_name": company.name}
