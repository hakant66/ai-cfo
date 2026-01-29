from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Iterable, List, Tuple

import stripe

from app.schemas import BalanceHistoryItem, PayoutItem, RevenueItem, StripeSyncRequest, TrueNetMarginItem

ZERO_DECIMAL_CURRENCIES = {
    "bif",
    "clp",
    "djf",
    "gnf",
    "jpy",
    "kmf",
    "krw",
    "mga",
    "pyg",
    "rwf",
    "ugx",
    "vnd",
    "vuv",
    "xaf",
    "xof",
    "xpf",
}


def _to_major(amount: int | None, currency: str) -> float:
    if amount is None:
        return 0.0
    if currency.lower() in ZERO_DECIMAL_CURRENCIES:
        return float(amount)
    return float(amount) / 100.0


def _describe_fx(source_currency: str | None, currency: str, exchange_rate: float | None) -> str | None:
    if not exchange_rate or not source_currency or source_currency.lower() == currency.lower():
        return None
    return f"FX {source_currency.upper()}->{currency.upper()} @ {exchange_rate}"


class StripeClient:
    def __init__(self, api_key: str, stripe_account: str | None = None) -> None:
        stripe.api_key = api_key
        self._stripe_account = stripe_account

    def _list_all(self, list_method, **params) -> Iterable:
        starting_after = None
        while True:
            if self._stripe_account:
                params["stripe_account"] = self._stripe_account
            page = list_method(starting_after=starting_after, **params)
            for item in page.data:
                yield item
            if not page.has_more:
                break
            starting_after = page.data[-1].id

    def _since_timestamp(self, days: int) -> int:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        return int(since.timestamp())

    def _date_range(self, start: date | None, end: date | None, default_days: int) -> Tuple[int, int]:
        now = datetime.now(timezone.utc)
        if not end:
            end_dt = now
        else:
            end_dt = datetime.combine(end, datetime.max.time()).replace(tzinfo=timezone.utc)
        if not start:
            start_dt = end_dt - timedelta(days=default_days)
        else:
            start_dt = datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc)
        if start_dt > end_dt:
            start_dt, end_dt = end_dt, start_dt
        return int(start_dt.timestamp()), int(end_dt.timestamp())

    def fetch_revenue(self, request: StripeSyncRequest, days: int = 30) -> List[RevenueItem]:
        since, until = self._date_range(request.start_date, request.end_date, days)
        items: List[RevenueItem] = []

        for bt in self._list_all(stripe.BalanceTransaction.list, created={"gte": since, "lte": until}, limit=100):
            fx_note = _describe_fx(getattr(bt, "source_currency", None), bt.currency, getattr(bt, "exchange_rate", None))
            description = bt.description or bt.type
            if fx_note:
                description = f"{description} ({fx_note})" if description else fx_note

            items.append(RevenueItem(
                date=datetime.fromtimestamp(bt.created, tz=timezone.utc),
                amount_gross=_to_major(bt.amount, bt.currency),
                fee=_to_major(bt.fee, bt.currency),
                amount_net=_to_major(bt.net, bt.currency),
                currency=bt.currency.upper(),
                status=bt.status or "unknown",
                description=description,
            ))

        for charge in self._list_all(
            stripe.Charge.list,
            created={"gte": since, "lte": until},
            expand=["data.balance_transaction"],
            limit=100,
        ):
            bt = charge.balance_transaction
            currency = charge.currency
            fee = _to_major(getattr(bt, "fee", None), currency) if bt else 0.0
            net = _to_major(getattr(bt, "net", None), currency) if bt else _to_major(charge.amount, currency)
            fx_note = None
            if bt:
                fx_note = _describe_fx(getattr(bt, "source_currency", None), bt.currency, getattr(bt, "exchange_rate", None))

            description = charge.description or f"Charge {charge.id}"
            tax_amount = getattr(charge, "amount_tax", None)
            if tax_amount:
                description = f"{description} (tax {_to_major(tax_amount, currency):.2f} {currency.upper()})"
            if fx_note:
                description = f"{description} ({fx_note})"

            items.append(RevenueItem(
                date=datetime.fromtimestamp(charge.created, tz=timezone.utc),
                amount_gross=_to_major(charge.amount, currency),
                fee=fee,
                amount_net=net,
                currency=currency.upper(),
                status=charge.status or "unknown",
                description=description,
            ))

        for refund in self._list_all(
            stripe.Refund.list,
            created={"gte": since, "lte": until},
            expand=["data.balance_transaction"],
            limit=100,
        ):
            bt = refund.balance_transaction
            currency = refund.currency
            if bt:
                amount_gross = _to_major(bt.amount, bt.currency)
                fee = _to_major(bt.fee, bt.currency)
                net = _to_major(bt.net, bt.currency)
                fx_note = _describe_fx(getattr(bt, "source_currency", None), bt.currency, getattr(bt, "exchange_rate", None))
            else:
                amount_gross = -abs(_to_major(refund.amount, currency))
                fee = 0.0
                net = amount_gross
                fx_note = None

            description = refund.reason or f"Refund {refund.id}"
            if fx_note:
                description = f"{description} ({fx_note})"

            items.append(RevenueItem(
                date=datetime.fromtimestamp(refund.created, tz=timezone.utc),
                amount_gross=amount_gross,
                fee=fee,
                amount_net=net,
                currency=currency.upper(),
                status=refund.status or "unknown",
                description=description,
            ))

        return items

    def fetch_balance_history(self, request: StripeSyncRequest, days: int = 7) -> List[BalanceHistoryItem]:
        since, until = self._date_range(request.start_date, request.end_date, days)
        items: List[BalanceHistoryItem] = []

        for bt in self._list_all(stripe.BalanceTransaction.list, created={"gte": since, "lte": until}, limit=100):
            items.append(BalanceHistoryItem(
                transaction_id=bt.id,
                date=datetime.fromtimestamp(bt.created, tz=timezone.utc),
                amount_gross=_to_major(bt.amount, bt.currency),
                fee=_to_major(bt.fee, bt.currency),
                amount_net=_to_major(bt.net, bt.currency),
                currency=bt.currency.upper(),
                status=bt.status or "unknown",
                type=bt.type or "unknown",
                source_id=str(getattr(bt, "source", None)) if getattr(bt, "source", None) else None,
                description=bt.description,
            ))

        return items

    def fetch_payouts(self, request: StripeSyncRequest, days: int = 7) -> List[PayoutItem]:
        since, until = self._date_range(request.start_date, request.end_date, days)
        items: List[PayoutItem] = []

        for payout in self._list_all(stripe.Payout.list, created={"gte": since, "lte": until}, limit=100):
            arrival = payout.arrival_date
            arrival_dt = datetime.fromtimestamp(arrival, tz=timezone.utc) if arrival else None
            items.append(PayoutItem(
                payout_id=payout.id,
                amount=_to_major(payout.amount, payout.currency),
                currency=payout.currency.upper(),
                status=payout.status or "unknown",
                arrival_date=arrival_dt,
                created_at=datetime.fromtimestamp(payout.created, tz=timezone.utc),
                method=getattr(payout, "method", None),
                payout_type=getattr(payout, "type", None),
            ))

        return items

    def fetch_true_net_margin(self, request: StripeSyncRequest, days: int = 7) -> List[TrueNetMarginItem]:
        since, until = self._date_range(request.start_date, request.end_date, days)
        limit = request.limit or 100
        items: List[TrueNetMarginItem] = []

        for bt in self._list_all(stripe.BalanceTransaction.list, created={"gte": since, "lte": until}, limit=limit):
            gross = _to_major(bt.amount, bt.currency)
            fee = _to_major(bt.fee, bt.currency)
            net = _to_major(bt.net, bt.currency)
            margin_pct = round((net / gross) * 100, 2) if gross > 0 else 0.0
            available_on = datetime.fromtimestamp(bt.available_on, tz=timezone.utc) if getattr(bt, "available_on", None) else None

            source_id = str(getattr(bt, "source", None)) if getattr(bt, "source", None) else None
            payment_intent_amount = None
            tax_amount = None
            customer_metadata = None

            if source_id and bt.type == "charge":
                charge = stripe.Charge.retrieve(source_id, stripe_account=self._stripe_account)
                payment_intent_amount = _to_major(getattr(charge, "amount", None), charge.currency)
                tax_amount = _to_major(getattr(charge, "amount_tax", None), charge.currency) if getattr(charge, "amount_tax", None) else None
                if getattr(charge, "customer", None):
                    customer = stripe.Customer.retrieve(charge.customer, stripe_account=self._stripe_account)
                    customer_metadata = getattr(customer, "metadata", None)

            items.append(TrueNetMarginItem(
                id=bt.id,
                type=bt.type or "unknown",
                date=datetime.fromtimestamp(bt.created, tz=timezone.utc),
                gross_amount=gross,
                stripe_fee=fee,
                net_amount=net,
                margin_pct=margin_pct,
                currency=bt.currency.upper(),
                available_on=available_on,
                payment_intent_amount=payment_intent_amount,
                tax_amount=tax_amount,
                customer_metadata=customer_metadata,
                source_id=source_id,
            ))

        return items
