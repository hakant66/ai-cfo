from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Company

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/")
def list_companies(db: Session = Depends(get_db)):
    return db.query(Company).all()
