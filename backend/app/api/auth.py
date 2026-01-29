from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user, require_roles
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.models import Company, User
from app.schemas.auth import UserCreate, UserLogin, Token, UserOut, AdminUserCreate, AdminUserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    company = Company(name=payload.company_name)
    db.add(company)
    db.flush()
    user = User(
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        company_id=company.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if payload.company_id is not None and user.company_id != payload.company_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(str(user.id))
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/admin/users", response_model=UserOut)
def admin_create_user(payload: AdminUserCreate, db: Session = Depends(get_db), user=Depends(require_roles(["Founder"]))):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    company = db.query(Company).filter(Company.id == payload.company_id).first()
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    new_user = User(
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        company_id=company.id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.get("/admin/users", response_model=list[UserOut])
def admin_list_users(company_id: int, db: Session = Depends(get_db), user=Depends(require_roles(["Founder"]))):
    return db.query(User).filter(User.company_id == company_id).order_by(User.created_at.desc()).all()


@router.patch("/admin/users/{user_id}", response_model=UserOut)
def admin_update_user(user_id: int, payload: AdminUserUpdate, db: Session = Depends(get_db), user=Depends(require_roles(["Founder"]))):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.email:
        existing = db.query(User).filter(User.email == payload.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        target.email = payload.email
    if payload.role:
        target.role = payload.role
    if payload.password:
        target.password_hash = get_password_hash(payload.password)
    db.commit()
    db.refresh(target)
    return target


@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_user(user_id: int, db: Session = Depends(get_db), user=Depends(require_roles(["Founder"]))):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if target.id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete current user")
    db.delete(target)
    db.commit()
    return None
