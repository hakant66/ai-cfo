from app.services.finance_brain import FinanceBrain


def test_weeks_of_cover_basic():
    woc = FinanceBrain.calculate_weeks_of_cover(700, [10] * 30)
    assert woc == 10.0


def test_weeks_of_cover_no_sales():
    woc = FinanceBrain.calculate_weeks_of_cover(100, [0] * 30)
    assert woc == float("inf")


def test_cash_forecast():
    forecast = FinanceBrain.cash_forecast(10000, 500, 2000, 7)
    assert forecast["best_case"] > forecast["expected"]
    assert forecast["expected"] > forecast["worst_case"]