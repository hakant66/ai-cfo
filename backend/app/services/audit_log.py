from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.models import AuditLog


def log_event(
    db: Session,
    company_id: int,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    actor_user_id: int | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        company_id=company_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata or {},
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
