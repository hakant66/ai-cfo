from sqlalchemy import text
from sqlalchemy.orm import Session


def _lock_key(company_id: int, provider: str, environment: str) -> int:
    return abs(hash(f"{company_id}:{provider}:{environment}")) % (2**31)


def try_advisory_lock(db: Session, company_id: int, provider: str, environment: str) -> bool:
    key = _lock_key(company_id, provider, environment)
    try:
        result = db.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key}).scalar()
        return bool(result)
    except Exception:
        return True


def release_advisory_lock(db: Session, company_id: int, provider: str, environment: str) -> None:
    key = _lock_key(company_id, provider, environment)
    try:
        db.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
    except Exception:
        return
