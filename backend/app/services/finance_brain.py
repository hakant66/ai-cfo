from datetime import datetime, timedelta, timezone
from typing import List, Dict


class FinanceBrain:
    @staticmethod
    def calculate_weeks_of_cover(inventory_on_hand: int, daily_sales_30d: List[int]) -> float:
        if not daily_sales_30d or sum(daily_sales_30d) == 0:
            return float("inf")
        avg_daily_sales = sum(daily_sales_30d) / 30
        return round(inventory_on_hand / avg_daily_sales / 7, 2)

    @staticmethod
    def calculate_aged_inventory_days(last_sold_date: datetime | None, first_received_date: datetime | None) -> int | None:
        if last_sold_date:
            return (datetime.now(timezone.utc) - last_sold_date).days
        if first_received_date:
            return (datetime.now(timezone.utc) - first_received_date).days
        return None

    @staticmethod
    def cash_forecast(current_balance: float, avg_daily_sales: float, payables_due: float, days: int) -> Dict[str, float]:
        expected_in = avg_daily_sales * days
        best_case = current_balance + expected_in * 1.1 - payables_due
        expected = current_balance + expected_in * 0.95 - payables_due
        worst_case = current_balance + expected_in * 0.75 - payables_due
        return {
            "best_case": round(best_case, 2),
            "expected": round(expected, 2),
            "worst_case": round(worst_case, 2),
        }

    @staticmethod
    def expected_payouts(net_sales: float, settlement_lag_days: int, window_days: int) -> float:
        lag_factor = 1 - min(settlement_lag_days / max(window_days, 1), 0.5)
        return round(net_sales * lag_factor, 2)

    @staticmethod
    def payables_due_within(payables: List[Dict], days: int) -> float:
        horizon = datetime.now(timezone.utc).date() + timedelta(days=days)
        total = 0.0
        for payable in payables:
            if payable["due_date"] <= horizon and payable["status"] == "open":
                total += payable["amount"]
        return round(total, 2)

    @staticmethod
    def supplier_lead_time_stats(purchase_orders: List[Dict]) -> Dict[str, float]:
        lead_times = []
        for po in purchase_orders:
            if po.get("received_date") and po.get("created_at"):
                lead_times.append((po["received_date"] - po["created_at"]).days)
        if not lead_times:
            return {"average": 0.0, "variance": 0.0}
        avg = sum(lead_times) / len(lead_times)
        variance = sum((lt - avg) ** 2 for lt in lead_times) / len(lead_times)
        return {"average": round(avg, 2), "variance": round(variance, 2)}

    @staticmethod
    def supplier_reliability_score(purchase_orders: List[Dict]) -> float:
        if not purchase_orders:
            return 0.0
        on_time = 0
        total = 0
        for po in purchase_orders:
            if po.get("received_date") and po.get("promised_date"):
                total += 1
                if po["received_date"] <= po["promised_date"]:
                    on_time += 1
        if total == 0:
            return 0.0
        return round(on_time / total, 2)