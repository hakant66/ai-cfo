from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.models import SyncRun


def start_sync_run(db: Session, company_id: int, provider: str, environment: str, trace_id: str | None = None) -> SyncRun:
    run = SyncRun(
        company_id=company_id,
        provider=provider,
        environment=environment,
        status="started",
        started_at=datetime.now(timezone.utc),
        trace_id=trace_id,
        counts={},
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def finish_sync_run(db: Session, run_id: int, status: str, counts: dict, error_summary: str | None = None) -> None:
    run = db.query(SyncRun).filter(SyncRun.id == run_id).first()
    if not run:
        return
    run.status = status
    run.ended_at = datetime.now(timezone.utc)
    run.counts = counts
    run.error_summary = error_summary
    db.commit()
