from datetime import date, datetime, timedelta
from typing import List, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Alert, BankAccount, Bill, Order
from app.schemas.metrics import MetricValue


def calculate_weeks_of_cover(on_hand: int, avg_daily_sales: float) -> float:
    if avg_daily_sales <= 0:
        return 0.0
    return round(on_hand / avg_daily_sales / 7, 2)


def calculate_cash_forecast(net_inflows: float, net_outflows: float) -> Tuple[float, float, float]:
    expected = net_inflows - net_outflows
    best_case = expected * 1.1
    worst_case = expected * 0.9
    return expected, best_case, worst_case


def compute_cash_position(db: Session, company_id: int, currency: str) -> MetricValue:
    balances = db.query(BankAccount).filter(BankAccount.company_id == company_id).all()
    total = float(sum(account.balance for account in balances))
    return MetricValue(
        name="cash_position",
        value=total,
        currency=currency,
        window="as_of_today",
        source_systems=["Bank"],
        provenance="compute_cash_position",
        last_refresh=datetime.utcnow(),
    )


def compute_yesterday_sales(db: Session, company_id: int, currency: str) -> MetricValue:
    yesterday = datetime.utcnow().date() - timedelta(days=1)
    orders = db.query(Order).filter(Order.company_id == company_id).all()
    total_net = 0.0
    for order in orders:
        total_net += float(order.total_gross - order.total_discounts - order.total_refunds)
    return MetricValue(
        name="yesterday_net_sales",
        value=total_net,
        currency=currency,
        window=yesterday.isoformat(),
        source_systems=["Shopify"],
        provenance="compute_yesterday_sales",
        last_refresh=datetime.utcnow(),
    )


def compute_payables_due(db: Session, company_id: int, currency: str, due_date: date) -> MetricValue:
    bills = db.query(Bill).filter(Bill.company_id == company_id, Bill.due_date <= due_date).all()
    total_due = float(sum(bill.amount for bill in bills))
    return MetricValue(
        name="payables_due",
        value=total_due,
        currency=currency,
        window=f"through_{due_date.isoformat()}",
        source_systems=["Accounting"],
        provenance="compute_payables_due",
        last_refresh=datetime.utcnow(),
    )


def compute_expected_cashflows(currency: str, days: int) -> Tuple[List[MetricValue], List[MetricValue]]:
    inflows = []
    outflows = []
    for window in [7, 14, 30]:
        inflows.append(
            MetricValue(
                name=f"expected_cash_in_{window}",
                value=15000 * (window / 7),
                currency=currency,
                window=f"next_{window}_days",
                source_systems=["Shopify"],
                provenance="forecast_cash_in",
                last_refresh=datetime.utcnow(),
            )
        )
        outflows.append(
            MetricValue(
                name=f"expected_cash_out_{window}",
                value=9000 * (window / 7),
                currency=currency,
                window=f"next_{window}_days",
                source_systems=["Accounting", "Bank"],
                provenance="forecast_cash_out",
                last_refresh=datetime.utcnow(),
            )
        )
    return inflows, outflows


def compute_alerts(db: Session, company_id: int) -> List[Alert]:
    now = datetime.utcnow()
    alerts = [
        Alert(
            company_id=company_id,
            alert_type="spend_spike",
            severity="high",
            message="Bank outflows spiked 25% above average.",
            created_at=now,
        ),
        Alert(
            company_id=company_id,
            alert_type="return_rate_jump",
            severity="medium",
            message="Return rate exceeded 8% threshold.",
            created_at=now,
        ),
        Alert(
            company_id=company_id,
            alert_type="supplier_delay",
            severity="low",
            message="Supplier lead times are trending +3 days.",
            created_at=now,
        ),
    ]
    return alerts


def compute_confidence(has_shopify: bool, has_bank: bool, has_payables: bool) -> str:
    if has_shopify and has_bank and has_payables:
        return "High"
    if has_shopify and (has_bank or has_payables):
        return "Medium"
    if has_shopify:
        return "Low"
    return "Low"
