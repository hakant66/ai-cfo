from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Company
from app.schemas.metrics import CashForecastResponse, InventoryHealthRow, MorningBriefResponse
from app.services.metrics import (
    calculate_cash_forecast,
    compute_cash_position,
    compute_confidence,
    compute_expected_cashflows,
    compute_payables_due,
    compute_yesterday_sales,
)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/morning_brief", response_model=MorningBriefResponse)
def morning_brief(date: str, db: Session = Depends(get_db)) -> MorningBriefResponse:
    company = db.query(Company).first()
    currency = company.currency if company else "USD"

    cash_position = compute_cash_position(db, company.id if company else 1, currency)
    cash_in, cash_out = compute_expected_cashflows(currency, 30)
    yesterday_sales = compute_yesterday_sales(db, company.id if company else 1, currency)
    payables = compute_payables_due(db, company.id if company else 1, currency, datetime.utcnow().date())

    confidence = compute_confidence(has_shopify=True, has_bank=True, has_payables=False)

    return MorningBriefResponse(
        cash_position=cash_position,
        expected_cash_in=cash_in,
        expected_cash_out=cash_out,
        yesterday_performance=[yesterday_sales],
        inventory_health=[],
        payables_due=[payables],
        alerts=[],
        confidence=confidence,
    )


@router.get("/cash_forecast", response_model=CashForecastResponse)
def cash_forecast(days: int = 7) -> CashForecastResponse:
    expected, best, worst = calculate_cash_forecast(12000.0, 8000.0)
    metric = {
        "name": "cash_forecast",
        "value": expected,
        "currency": "USD",
        "window": f"next_{days}_days",
        "source_systems": ["Shopify", "Bank"],
        "provenance": "calculate_cash_forecast",
        "last_refresh": datetime.utcnow(),
    }
    return CashForecastResponse(
        days=days,
        expected=metric,
        best_case={**metric, "value": best},
        worst_case={**metric, "value": worst},
    )


@router.get("/inventory_health", response_model=list[InventoryHealthRow])
def inventory_health() -> list[InventoryHealthRow]:
    return [
        InventoryHealthRow(
            sku="SKU-RED-42",
            on_hand=120,
            avg_daily_sales=8,
            weeks_of_cover=2.1,
            stockout_risk=True,
            overstock_risk=False,
        ),
        InventoryHealthRow(
            sku="SKU-BLUE-10",
            on_hand=480,
            avg_daily_sales=4,
            weeks_of_cover=17.1,
            stockout_risk=False,
            overstock_risk=True,
        ),
    ]
