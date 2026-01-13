from app.services.metrics import calculate_cash_forecast, calculate_weeks_of_cover, compute_alerts


def test_calculate_weeks_of_cover():
    assert calculate_weeks_of_cover(70, 10) == 1.0
    assert calculate_weeks_of_cover(0, 0) == 0.0


def test_calculate_cash_forecast():
    expected, best, worst = calculate_cash_forecast(1000, 800)
    assert expected == 200
    assert best == 220
    assert worst == 180


def test_alert_generation():
    alerts = compute_alerts(db=None, company_id=1)
    types = {alert.alert_type for alert in alerts}
    assert {"spend_spike", "return_rate_jump", "supplier_delay"} == types
