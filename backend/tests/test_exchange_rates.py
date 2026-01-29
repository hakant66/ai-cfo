import requests

from app.models.models import Company, ExchangeRate
from app.services.exchange_rates import SUPPORTED_PAIRS, refresh_exchange_rates


def test_refresh_exchange_rates_uses_fallback_and_cross_rates(monkeypatch, db_session):
    company = Company(name="FX Co")
    db_session.add(company)
    db_session.flush()

    calls = []

    def fake_get(url, timeout):
        calls.append(url)

        class Response:
            def __init__(self, status_code, payload, error=None):
                self.status_code = status_code
                self._payload = payload
                self._error = error

            def raise_for_status(self):
                if self._error:
                    raise self._error
                if self.status_code >= 400:
                    raise requests.HTTPError(f"{self.status_code}")

            def json(self):
                return self._payload

        if "open.er-api.com" in url:
            return Response(502, {"result": "error"}, error=requests.HTTPError("bad gateway"))
        if "exchangerate.host" in url:
            return Response(
                200,
                {"success": True, "rates": {"USD": 1.0, "EUR": 0.9, "GBP": 0.8, "CNY": 7.1, "TRY": 32.0}},
            )
        raise AssertionError(f"Unexpected URL {url}")

    monkeypatch.setattr("requests.get", fake_get)

    result = refresh_exchange_rates(db_session, company.id)
    assert result["updated"] == len(SUPPORTED_PAIRS)

    rows = db_session.query(ExchangeRate).filter(ExchangeRate.company_id == company.id).all()
    assert len(rows) == len(SUPPORTED_PAIRS)
    rate_map = {row.pair: row.rate for row in rows}

    expected_eur_gbp = 0.8 / 0.9
    assert abs(rate_map["EUR/GBP"] - expected_eur_gbp) < 1e-9
    assert all(not row.manual_override for row in rows)

    assert any("open.er-api.com" in call for call in calls)
    assert any("exchangerate.host" in call for call in calls)
