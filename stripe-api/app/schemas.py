from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class StripeSyncRequest(BaseModel):
    stripe_account: Optional[str] = None
    publishable_key: Optional[str] = None
    secret_key: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    limit: Optional[int] = None


class RevenueItem(BaseModel):
    date: datetime
    amount_gross: float = Field(..., description="Gross amount in major currency units.")
    fee: float = Field(..., description="Fee amount in major currency units.")
    amount_net: float = Field(..., description="Net amount in major currency units.")
    currency: str
    status: str
    description: Optional[str] = None


class RevenueSyncResponse(BaseModel):
    items: List[RevenueItem]
    count: int


class BalanceHistoryItem(BaseModel):
    transaction_id: str
    date: datetime
    amount_gross: float
    fee: float
    amount_net: float
    currency: str
    status: str
    type: str
    source_id: Optional[str] = None
    description: Optional[str] = None


class PayoutItem(BaseModel):
    payout_id: str
    amount: float
    currency: str
    status: str
    arrival_date: Optional[datetime] = None
    created_at: datetime
    method: Optional[str] = None
    payout_type: Optional[str] = None


class BalancePayoutsResponse(BaseModel):
    balance_history: List[BalanceHistoryItem]
    payouts: List[PayoutItem]
    balance_count: int
    payout_count: int


class TrueNetMarginItem(BaseModel):
    id: str
    type: str
    date: datetime
    gross_amount: float
    stripe_fee: float
    net_amount: float
    margin_pct: float
    currency: str
    available_on: Optional[datetime] = None
    payment_intent_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    customer_metadata: Optional[dict] = None
    source_id: Optional[str] = None


class TrueNetMarginResponse(BaseModel):
    items: List[TrueNetMarginItem]
    count: int
