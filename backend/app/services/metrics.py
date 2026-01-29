from datetime import datetime, timedelta, timezone, date
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import (
    Order, Refund, InventorySnapshot, Bill, BankAccount, BankBalance, MetricRun, Alert, Company, MarketingSpend
)
from app.services.finance_brain import FinanceBrain
from app.services.completeness import compute_confidence


def _metric(value: Any, currency: str | None, time_window: str, sources: list, provenance: str, query_id: str) -> Dict[str, Any]:
    return {
        "value": value,
        "currency": currency,
        "time_window": time_window,
        "sources": sources,
        "provenance": provenance,
        "last_refresh": datetime.now(timezone.utc).isoformat(),
        "query_id": query_id,
    }


def record_metric(db: Session, company_id: int, metric_name: str, metric: Dict[str, Any]) -> MetricRun:
    metric_run = MetricRun(
        company_id=company_id,
        metric_name=metric_name,
        value=metric["value"],
        currency=metric.get("currency"),
        time_window=metric.get("time_window"),
        sources=metric.get("sources"),
        provenance=metric.get("provenance"),
        last_refresh=datetime.now(timezone.utc),
        query_id=metric.get("query_id") or metric_name,
    )
    db.add(metric_run)
    db.commit()
    db.refresh(metric_run)
    return metric_run


def _company_currency(db: Session, company_id: int) -> str:
    company = db.query(Company).filter(Company.id == company_id).first()
    return company.currency if company else "USD"


def _cash_position_by_provider(db: Session, company_id: int) -> dict[str, float]:
    latest = db.query(
        BankBalance.bank_account_id,
        func.max(BankBalance.captured_at).label("max_captured"),
    ).filter(
        BankBalance.company_id == company_id
    ).group_by(BankBalance.bank_account_id).subquery()
    balances = db.query(BankBalance, BankAccount).join(
        latest,
        (BankBalance.bank_account_id == latest.c.bank_account_id) &
        (BankBalance.captured_at == latest.c.max_captured),
    ).join(
        BankAccount,
        BankBalance.bank_account_id == BankAccount.id,
    ).all()
    totals: dict[str, float] = {}
    if balances:
        for balance, account in balances:
            provider = (account.provider or "manual").lower()
            key = "Wise" if provider == "wise" else "Bank"
            totals[key] = totals.get(key, 0.0) + float(balance.balance or 0)
        return totals
    accounts = db.query(BankAccount).filter(BankAccount.company_id == company_id).all()
    for account in accounts:
        provider = (account.provider or "manual").lower()
        key = "Wise" if provider == "wise" else "Bank"
        totals[key] = totals.get(key, 0.0) + float(account.balance or 0)
    return totals


def get_cash_position(db: Session, company_id: int) -> Dict[str, Any]:
    totals = _cash_position_by_provider(db, company_id)
    total_balance = sum(totals.values()) if totals else 0.0
    sources = []
    if totals.get("Bank"):
        sources.append("Bank")
    if totals.get("Wise"):
        sources.append("Wise")
    if not sources:
        sources = ["Bank"]
    metric = _metric(
        value=round(total_balance, 2),
        currency=_company_currency(db, company_id),
        time_window="current",
        sources=sources,
        provenance="metrics.get_cash_position",
        query_id="cash_position_v1",
    )
    metric["by_provider"] = {
        "bank": round(totals.get("Bank", 0.0), 2),
        "wise": round(totals.get("Wise", 0.0), 2),
    }
    return metric


def get_net_sales(db: Session, company_id: int, target_date: datetime) -> Dict[str, Any]:
    start = datetime(target_date.year, target_date.month, target_date.day)
    end = start + timedelta(days=1)
    orders = db.query(Order).filter(
        Order.company_id == company_id,
        Order.created_at >= start,
        Order.created_at < end,
    ).all()
    net_sales = sum(order.net_sales for order in orders) if orders else 0.0
    return _metric(
        value=round(net_sales, 2),
        currency=_company_currency(db, company_id),
        time_window=f"{start.date().isoformat()}",
        sources=["Shopify"],
        provenance="metrics.get_net_sales",
        query_id="net_sales_v1",
    )


def get_discounts(db: Session, company_id: int, target_date: datetime) -> Dict[str, Any]:
    start = datetime(target_date.year, target_date.month, target_date.day)
    end = start + timedelta(days=1)
    orders = db.query(Order).filter(
        Order.company_id == company_id,
        Order.created_at >= start,
        Order.created_at < end,
    ).all()
    discounts = sum(order.discounts for order in orders) if orders else 0.0
    return _metric(
        value=round(discounts, 2),
        currency=_company_currency(db, company_id),
        time_window=f"{start.date().isoformat()}",
        sources=["Shopify"],
        provenance="metrics.get_discounts",
        query_id="discounts_v1",
    )


def get_refunds(db: Session, company_id: int, target_date: datetime) -> Dict[str, Any]:
    start = datetime(target_date.year, target_date.month, target_date.day)
    end = start + timedelta(days=1)
    refunds = db.query(Refund).join(Order, Refund.order_id == Order.id).filter(
        Order.company_id == company_id,
        Refund.created_at >= start,
        Refund.created_at < end,
    ).all()
    total = sum(refund.amount for refund in refunds) if refunds else 0.0
    return _metric(
        value=round(total, 2),
        currency=_company_currency(db, company_id),
        time_window=f"{start.date().isoformat()}",
        sources=["Shopify"],
        provenance="metrics.get_refunds",
        query_id="refunds_v1",
    )


def get_ad_spend(db: Session, company_id: int, target_date: datetime) -> Dict[str, Any]:
    start = target_date.date()
    spend = db.query(MarketingSpend).filter(
        MarketingSpend.company_id == company_id,
        MarketingSpend.spend_date == start,
    ).all()
    total = sum(s.amount for s in spend) if spend else 0.0
    return _metric(
        value=round(total, 2),
        currency=_company_currency(db, company_id),
        time_window=f"{start.isoformat()}",
        sources=["Marketing"],
        provenance="metrics.get_ad_spend",
        query_id="ad_spend_v1",
    )


def get_mock_cogs(net_sales_metric: Dict[str, Any]) -> Dict[str, Any]:
    net_sales = float(net_sales_metric.get("value") or 0)
    return _metric(
        value=round(net_sales * 0.30, 2),
        currency=net_sales_metric.get("currency"),
        time_window=net_sales_metric.get("time_window"),
        sources=["Mock"],
        provenance="metrics.get_mock_cogs",
        query_id="mock_cogs_v1",
    )


def get_mock_ad_spend(net_sales_metric: Dict[str, Any]) -> Dict[str, Any]:
    net_sales = float(net_sales_metric.get("value") or 0)
    return _metric(
        value=round(net_sales * 0.10, 2),
        currency=net_sales_metric.get("currency"),
        time_window=net_sales_metric.get("time_window"),
        sources=["Mock"],
        provenance="metrics.get_mock_ad_spend",
        query_id="mock_ad_spend_v1",
    )


def get_mock_other_expenses(net_sales_metric: Dict[str, Any]) -> Dict[str, Any]:
    net_sales = float(net_sales_metric.get("value") or 0)
    return _metric(
        value=round(net_sales * 0.10, 2),
        currency=net_sales_metric.get("currency"),
        time_window=net_sales_metric.get("time_window"),
        sources=["Mock"],
        provenance="metrics.get_mock_other_expenses",
        query_id="mock_other_expenses_v1",
    )


def get_gross_margin(net_sales_metric: Dict[str, Any], cogs_metric: Dict[str, Any]) -> Dict[str, Any]:
    net_sales = float(net_sales_metric.get("value") or 0)
    cogs = float(cogs_metric.get("value") or 0)
    return _metric(
        value=round(net_sales - cogs, 2),
        currency=net_sales_metric.get("currency"),
        time_window=net_sales_metric.get("time_window"),
        sources=["Shopify", "Mock"],
        provenance="metrics.get_gross_margin",
        query_id="gross_margin_v1",
    )


def get_contribution_margin(
    net_sales_metric: Dict[str, Any],
    cogs_metric: Dict[str, Any],
    ad_spend_metric: Dict[str, Any],
    other_expenses_metric: Dict[str, Any],
) -> Dict[str, Any]:
    net_sales = float(net_sales_metric.get("value") or 0)
    cogs = float(cogs_metric.get("value") or 0)
    ad_spend = float(ad_spend_metric.get("value") or 0)
    other = float(other_expenses_metric.get("value") or 0)
    return _metric(
        value=round(net_sales - cogs - ad_spend - other, 2),
        currency=net_sales_metric.get("currency"),
        time_window=net_sales_metric.get("time_window"),
        sources=["Shopify", "Mock"],
        provenance="metrics.get_contribution_margin",
        query_id="contribution_margin_v1",
    )


def get_inventory_health(db: Session, company_id: int) -> Dict[str, Any]:
    snapshots = db.query(InventorySnapshot).filter(
        InventorySnapshot.snapshot_date == datetime.now(timezone.utc).date(),
        InventorySnapshot.company_id == company_id,
    ).all()
    items = []
    for snap in snapshots:
        divisor = 7 + (sum(ord(char) for char in snap.sku) % 4)
        avg_daily_sales = round(snap.on_hand / divisor, 2) if snap.on_hand else 0.0
        if avg_daily_sales > 0:
            weeks = round(snap.on_hand / avg_daily_sales / 7, 2)
        else:
            weeks = float("inf")
        weeks_value = None if weeks == float("inf") else weeks
        stockout = weeks_value is not None and weeks_value < 2
        overstock = weeks_value is not None and weeks_value > 12
        items.append({
            "sku": snap.sku,
            "on_hand": snap.on_hand,
            "avg_daily_units_sold": avg_daily_sales,
            "weeks_of_cover": weeks_value,
            "stockout_risk": stockout,
            "overstock_risk": overstock,
            "aged_inventory_days": None,
        })
    return {
        "items": items,
        "confidence": compute_confidence(db, company_id),
    }


def get_payables_due(db: Session, company_id: int, days: int) -> Dict[str, Any]:
    horizon = datetime.now(timezone.utc).date() + timedelta(days=days)
    bills = db.query(Bill).filter(
        Bill.company_id == company_id,
        Bill.status == "open",
        Bill.due_date <= horizon,
    ).all()
    total = sum(bill.amount for bill in bills) if bills else 0.0
    return _metric(
        value=round(total, 2),
        currency=_company_currency(db, company_id),
        time_window=f"next_{days}_days",
        sources=["Accounting"],
        provenance="metrics.get_payables_due",
        query_id=f"payables_due_{days}d_v1",
    )


def list_payables(
    db: Session,
    company_id: int,
    days: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> Dict[str, Any]:
    horizon = None
    use_range = start_date is not None or end_date is not None
    if not use_range and days is not None:
        horizon = datetime.now(timezone.utc).date() + timedelta(days=days)
    query = db.query(Bill).filter(Bill.company_id == company_id)
    if use_range:
        if start_date is not None:
            query = query.filter(Bill.due_date >= start_date)
        if end_date is not None:
            query = query.filter(Bill.due_date <= end_date)
    elif horizon:
        query = query.filter(Bill.due_date <= horizon)
    bills = query.order_by(Bill.due_date.asc()).all()
    items = []
    for bill in bills:
        items.append(
            {
                "id": bill.id,
                "vendor": bill.vendor,
                "amount": round(bill.amount, 2),
                "currency": _company_currency(db, company_id),
                "due_date": bill.due_date.isoformat(),
                "status": bill.status,
                "criticality": bill.criticality,
                "recommended_payment_date": bill.due_date.isoformat(),
            }
        )
    if use_range:
        window_label = f"{start_date.isoformat() if start_date else 'open'}_to_{end_date.isoformat() if end_date else 'open'}"
    else:
        window_label = f"next_{days}_days" if days is not None else "all_open"
    return {
        "items": items,
        "count": len(items),
        "time_window": window_label,
        "sources": ["Accounting"],
        "provenance": "metrics.list_payables",
        "last_refresh": datetime.now(timezone.utc).isoformat(),
        "query_id": f"payables_list_{window_label}",
    }


def get_cash_forecast(db: Session, company_id: int, days: int) -> Dict[str, Any]:
    cash_position = get_cash_position(db, company_id)
    avg_daily_sales = 0.0
    payables_total = get_payables_due(db, company_id, days)["value"]
    forecast = FinanceBrain.cash_forecast(cash_position["value"], avg_daily_sales, payables_total, days)
    currency = _company_currency(db, company_id)
    return {
        "window_days": days,
        "best_case": _metric(forecast["best_case"], currency, f"next_{days}_days", ["Bank"], "metrics.cash_forecast", f"cash_forecast_{days}d_best"),
        "expected": _metric(forecast["expected"], currency, f"next_{days}_days", ["Bank"], "metrics.cash_forecast", f"cash_forecast_{days}d_expected"),
        "worst_case": _metric(forecast["worst_case"], currency, f"next_{days}_days", ["Bank"], "metrics.cash_forecast", f"cash_forecast_{days}d_worst"),
        "confidence": compute_confidence(db, company_id),
    }


def get_morning_brief(db: Session, company_id: int, target_date: datetime) -> Dict[str, Any]:
    latest_order = db.query(Order.created_at).filter(
        Order.company_id == company_id
    ).order_by(Order.created_at.desc()).first()
    if latest_order:
        latest_date = latest_order[0].date()
        day_start = datetime(target_date.year, target_date.month, target_date.day)
        day_end = day_start + timedelta(days=1)
        has_orders = db.query(Order.id).filter(
            Order.company_id == company_id,
            Order.created_at >= day_start,
            Order.created_at < day_end,
        ).first() is not None
        if not has_orders:
            target_date = datetime.combine(latest_date, datetime.min.time())

    cash = get_cash_position(db, company_id)
    expected_cash = {
        "7d": get_cash_forecast(db, company_id, 7)["expected"],
        "14d": get_cash_forecast(db, company_id, 14)["expected"],
        "30d": get_cash_forecast(db, company_id, 30)["expected"],
    }
    net_sales = get_net_sales(db, company_id, target_date)
    refunds = get_refunds(db, company_id, target_date)
    discounts = get_discounts(db, company_id, target_date)
    cogs = get_mock_cogs(net_sales)
    ad_spend = get_mock_ad_spend(net_sales)
    other_expenses = get_mock_other_expenses(net_sales)
    gross_margin = get_gross_margin(net_sales, cogs)
    contribution_margin = get_contribution_margin(net_sales, cogs, ad_spend, other_expenses)

    payables = {
        "7d": get_payables_due(db, company_id, 7),
        "30d": get_payables_due(db, company_id, 30),
    }
    alerts = db.query(Alert).filter(Alert.company_id == company_id).all()
    return {
        "cash_position": cash,
        "cash_position_breakdown": {
            "bank": _metric(
                value=cash.get("by_provider", {}).get("bank"),
                currency=cash.get("currency"),
                time_window="current",
                sources=["Bank"],
                provenance="metrics.get_cash_position",
                query_id="cash_position_bank_v1",
            ),
            "wise": _metric(
                value=cash.get("by_provider", {}).get("wise"),
                currency=cash.get("currency"),
                time_window="current",
                sources=["Wise"],
                provenance="metrics.get_cash_position",
                query_id="cash_position_wise_v1",
            ),
        },
        "expected_cash": expected_cash,
        "yesterday_performance": {
            "net_sales": net_sales,
            "cogs": cogs,
            "gross_margin": gross_margin,
            "refunds": refunds,
            "discounts": discounts,
            "ad_spend": ad_spend,
            "other_expenses": other_expenses,
            "contribution_margin": contribution_margin,
        },
        "inventory_health": {
            "placeholder": _metric("see /metrics/inventory_health", None, "current", ["Inventory"], "metrics.inventory_health", "inventory_health_link"),
        },
        "payables": payables,
        "alerts": [
            {
                "id": alert.id,
                "type": alert.alert_type.value,
                "severity": alert.severity.value,
                "message": alert.message,
            } for alert in alerts
        ],
        "confidence": compute_confidence(db, company_id),
    }
