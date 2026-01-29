from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class MetricValue(BaseModel):
    value: Any
    currency: Optional[str] = None
    time_window: str
    sources: List[str]
    provenance: str
    last_refresh: str
    query_id: str


class MorningBrief(BaseModel):
    cash_position: MetricValue
    expected_cash: Dict[str, MetricValue]
    yesterday_performance: Dict[str, MetricValue]
    inventory_health: Dict[str, MetricValue]
    payables: Dict[str, MetricValue]
    alerts: List[Dict[str, Any]]
    confidence: str


class InventoryHealthItem(BaseModel):
    sku: str
    on_hand: int
    avg_daily_units_sold: float
    weeks_of_cover: float
    stockout_risk: bool
    overstock_risk: bool
    aged_inventory_days: Optional[int]


class InventoryHealthResponse(BaseModel):
    items: List[InventoryHealthItem]
    confidence: str


class CashForecastResponse(BaseModel):
    window_days: int
    best_case: MetricValue
    expected: MetricValue
    worst_case: MetricValue
    confidence: str