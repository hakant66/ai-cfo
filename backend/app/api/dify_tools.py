from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.services.metrics import get_morning_brief, get_inventory_health, get_cash_forecast, list_payables
from app.services.documents import search_document_chunks

router = APIRouter(prefix="/tools", tags=["dify-tools"])


@router.get("/morning-brief")
def dify_morning_brief(
    date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    target = datetime.strptime(date, "%Y-%m-%d")
    return get_morning_brief(db, user.company_id, target)


@router.get("/cash-forecast")
def dify_cash_forecast(
    days: int = Query(14, ge=1, le=365),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return get_cash_forecast(db, user.company_id, days)


@router.get("/inventory-health")
def dify_inventory_health(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return get_inventory_health(db, user.company_id)


@router.get("/payables")
def dify_payables(
    days: int | None = Query(None, ge=1, le=365),
    start_date: str | None = Query(None, description="YYYY-MM-DD"),
    end_date: str | None = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
    return list_payables(db, user.company_id, days, parsed_start, parsed_end)


@router.get("/documents/search")
def dify_search_documents(
    query: str = Query(..., min_length=2),
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    results = search_document_chunks(db, user.company_id, query, limit=limit)
    return {
        "query": query,
        "results": results,
        "sources": ["Documents"],
        "provenance": "documents.search_document_chunks",
    }
