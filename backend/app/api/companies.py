from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.models import Company, User
from app.schemas.company import CompanyOut, CompanyUpdate, CompanyCreate, CompanyPublic

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/me", response_model=CompanyOut)
def get_company(db: Session = Depends(get_db), user=Depends(get_current_user)):
    company = db.query(Company).filter(Company.id == user.company_id).first()
    return company


@router.get("/public", response_model=list[CompanyPublic])
def list_public_companies(db: Session = Depends(get_db)):
    return db.query(Company).order_by(Company.name.asc()).all()


@router.patch("/me", response_model=CompanyOut)
def update_company(payload: CompanyUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    company = db.query(Company).filter(Company.id == user.company_id).first()
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(company, key, value)
    db.commit()
    db.refresh(company)
    return company


@router.get("", response_model=list[CompanyOut])
def list_companies(db: Session = Depends(get_db), user=Depends(require_roles(["Founder"]))):
    return db.query(Company).order_by(Company.created_at.desc()).all()


@router.get("/{company_id}", response_model=CompanyOut)
def get_company_by_id(company_id: int, db: Session = Depends(get_db), user=Depends(require_roles(["Founder"]))):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


@router.post("", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db), user=Depends(require_roles(["Founder"]))):
    company = Company(
        name=payload.name,
        website=payload.website,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        currency=payload.currency,
        timezone=payload.timezone,
        settlement_lag_days=payload.settlement_lag_days,
        thresholds=payload.thresholds or {},
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.patch("/{company_id}", response_model=CompanyOut)
def update_company_by_id(company_id: int, payload: CompanyUpdate, db: Session = Depends(get_db), user=Depends(require_roles(["Founder"]))):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    for key, value in payload.dict(exclude_unset=True).items():
        setattr(company, key, value)
    db.commit()
    db.refresh(company)
    return company


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(company_id: int, db: Session = Depends(get_db), user=Depends(require_roles(["Founder"]))):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    has_users = db.query(User).filter(User.company_id == company_id).count() > 0
    if has_users:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Company has active users")
    db.delete(company)
    db.commit()
    return None
