from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel


class MetricValue(BaseModel):
    name: str
    value: float
    currency: Optional[str] = None
    window: str
    source_systems: List[str]
    provenance: str
    last_refresh: datetime


class MorningBriefResponse(BaseModel):
    cash_position: MetricValue
    expected_cash_in: List[MetricValue]
    expected_cash_out: List[MetricValue]
    yesterday_performance: List[MetricValue]
    inventory_health: List[MetricValue]
    payables_due: List[MetricValue]
    alerts: List[str]
    confidence: str


class InventoryHealthRow(BaseModel):
    sku: str
    on_hand: int
    avg_daily_sales: float
    weeks_of_cover: float
    stockout_risk: bool
    overstock_risk: bool


class CashForecastResponse(BaseModel):
    days: int
    expected: MetricValue
    best_case: MetricValue
    worst_case: MetricValue


class AlertResponse(BaseModel):
    alert_type: str
    severity: str
    message: str
    created_at: datetime


class MorningBriefQuery(BaseModel):
    date: date
