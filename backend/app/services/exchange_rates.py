from datetime import datetime, timezone
from typing import Callable, Dict, Iterable

import requests
from sqlalchemy.orm import Session

from app.models.models import Company, ExchangeRate

BASE_CURRENCY = "USD"

SUPPORTED_PAIRS = [
    ("EUR", "GBP"),
    ("GBP", "USD"),
    ("EUR", "USD"),
    ("CNY", "USD"),
    ("CNY", "GBP"),
    ("CNY", "EUR"),
    ("GBP", "TRY"),
    ("USD", "TRY"),
    ("EUR", "TRY"),
]

def _normalize_pairs(pairs: Iterable[str]) -> list[str]:
    normalized = []
    for pair in pairs:
        if not isinstance(pair, str):
            continue
        clean = pair.replace('"', "").replace("'", "").strip().upper()
        if clean and "/" in clean:
            normalized.append(clean)
    return normalized


def _tracked_pairs(db: Session, company_id: int) -> list[str]:
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company or not company.thresholds:
        return []
    tracked = company.thresholds.get("tracked_currency_pairs")
    if not isinstance(tracked, list):
        return []
    return _normalize_pairs(tracked)


def _parse_open_er_api(payload: dict) -> Dict[str, float]:
    if payload.get("result") != "success":
        raise ValueError("Open ER API returned error")
    return payload.get("rates", {})


def _parse_exchangerate_host(payload: dict) -> Dict[str, float]:
    if not payload.get("success", True):
        raise ValueError("ExchangeRate.host returned error")
    return payload.get("rates", {})


def _fetch_rates(base_code: str) -> Dict[str, float]:
    providers: Iterable[tuple[str, str, Callable[[dict], Dict[str, float]]]] = [
        ("open.er-api.com", f"https://open.er-api.com/v6/latest/{base_code}", _parse_open_er_api),
        ("exchangerate.host", f"https://api.exchangerate.host/latest?base={base_code}", _parse_exchangerate_host),
    ]
    last_error: Exception | None = None
    for _, url, parser in providers:
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            payload = response.json()
            rates = parser(payload)
            if rates:
                return rates
            raise ValueError("Exchange rate provider returned empty rates")
        except Exception as exc:
            last_error = exc
    raise ValueError("All exchange rate providers failed") from last_error


def _fetch_base_rates(required_currencies: Iterable[str]) -> Dict[str, float]:
    rates = _fetch_rates(BASE_CURRENCY)
    rates[BASE_CURRENCY] = 1.0
    return rates


def _cross_rate(base: str, quote: str, usd_rates: Dict[str, float]) -> float | None:
    if base == BASE_CURRENCY:
        return usd_rates.get(quote)
    base_rate = usd_rates.get(base)
    quote_rate = usd_rates.get(quote)
    if base_rate is None or quote_rate is None:
        return None
    return quote_rate / base_rate


def _pairs_from_tracked(tracked_pairs: list[str]) -> list[tuple[str, str]]:
    pairs = []
    for pair in tracked_pairs:
        if "/" not in pair:
            continue
        base, quote = pair.split("/", 1)
        pairs.append((base, quote))
    return pairs


def refresh_exchange_rates(db: Session, company_id: int) -> dict:
    tracked_pairs = _tracked_pairs(db, company_id)
    tracked_set = set(tracked_pairs)
    pairs = SUPPORTED_PAIRS if not tracked_set else _pairs_from_tracked(tracked_pairs)
    required_currencies = {BASE_CURRENCY}
    for base, quote in pairs:
        required_currencies.add(base)
        required_currencies.add(quote)

    usd_rates = _fetch_base_rates(required_currencies)
    updated_at = datetime.now(timezone.utc)
    updated = 0

    for base, quote in pairs:
        rate = _cross_rate(base, quote, usd_rates)
        if rate is None:
            continue
        pair = f"{base}/{quote}"
        existing = db.query(ExchangeRate).filter(
            ExchangeRate.pair == pair,
            ExchangeRate.company_id == company_id,
        ).first()
        if existing:
            existing.rate = float(rate)
            existing.updated_at = updated_at
            existing.manual_override = False
        else:
            db.add(ExchangeRate(
                company_id=company_id,
                pair=pair,
                rate=float(rate),
                updated_at=updated_at,
                manual_override=False,
            ))
        updated += 1

    db.commit()
    return {"updated": updated, "updated_at": updated_at.isoformat()}


def list_exchange_rates(db: Session, company_id: int) -> list[dict]:
    tracked_pairs = _tracked_pairs(db, company_id)
    query = db.query(ExchangeRate).filter(
        ExchangeRate.company_id == company_id
    )
    if tracked_pairs:
        query = query.filter(ExchangeRate.pair.in_(tracked_pairs))
    rows = query.order_by(ExchangeRate.pair.asc()).all()
    return [
        {
            "pair": row.pair,
            "rate": row.rate,
            "updated_at": row.updated_at.isoformat(),
            "manual_override": row.manual_override,
        }
        for row in rows
    ]


def update_exchange_rate(db: Session, company_id: int, pair: str, rate: float) -> dict:
    now = datetime.now(timezone.utc)
    existing = db.query(ExchangeRate).filter(
        ExchangeRate.pair == pair,
        ExchangeRate.company_id == company_id,
    ).first()
    if not existing:
        existing = ExchangeRate(company_id=company_id, pair=pair, rate=rate, updated_at=now, manual_override=True)
        db.add(existing)
    else:
        existing.rate = rate
        existing.updated_at = now
        existing.manual_override = True
    db.commit()
    return {"pair": existing.pair, "rate": existing.rate, "updated_at": existing.updated_at.isoformat(), "manual_override": existing.manual_override}
