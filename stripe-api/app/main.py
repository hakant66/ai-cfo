import asyncio
import os
from typing import List

from fastapi import FastAPI, HTTPException

from app.schemas import BalancePayoutsResponse, RevenueItem, RevenueSyncResponse, StripeSyncRequest, TrueNetMarginResponse
from app.stripe_cl import StripeClient

app = FastAPI(title="Stripe API", version="0.1.0")


def _stripe_client(payload: StripeSyncRequest) -> StripeClient:
    api_key = payload.secret_key or os.getenv("STRIPE_SECRET_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="STRIPE_SECRET_KEY not configured.")
    return StripeClient(api_key, payload.stripe_account)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/sync/revenue", response_model=RevenueSyncResponse)
def sync_revenue(payload: StripeSyncRequest | None = None) -> RevenueSyncResponse:
    payload = payload or StripeSyncRequest()
    client = _stripe_client(payload)
    items: List[RevenueItem] = client.fetch_revenue(payload, days=30)
    return RevenueSyncResponse(items=items, count=len(items))


@app.post("/sync/balance-payouts", response_model=BalancePayoutsResponse)
async def sync_balance_payouts(payload: StripeSyncRequest | None = None) -> BalancePayoutsResponse:
    payload = payload or StripeSyncRequest()
    client = _stripe_client(payload)

    balance_task = asyncio.to_thread(client.fetch_balance_history, payload, 7)
    payout_task = asyncio.to_thread(client.fetch_payouts, payload, 7)
    balance_history, payouts = await asyncio.gather(balance_task, payout_task)

    return BalancePayoutsResponse(
        balance_history=balance_history,
        payouts=payouts,
        balance_count=len(balance_history),
        payout_count=len(payouts),
    )


@app.post("/metrics/true-net-margin", response_model=TrueNetMarginResponse)
async def true_net_margin(payload: StripeSyncRequest | None = None) -> TrueNetMarginResponse:
    payload = payload or StripeSyncRequest()
    client = _stripe_client(payload)

    items = await asyncio.to_thread(client.fetch_true_net_margin, payload, 7)
    return TrueNetMarginResponse(items=items, count=len(items))
