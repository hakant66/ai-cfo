from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.models import Company, Order, OrderLine


@dataclass(frozen=True)
class Window:
    start: date
    end: date
    timezone: str

    def to_dict(self) -> dict[str, str]:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "timezone": self.timezone,
        }


def _window_bounds(window: Window) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(window.start, time.min)
    end_dt = datetime.combine(window.end + timedelta(days=1), time.min)
    return start_dt, end_dt


def _confidence_from_coverage(coverage: float | None) -> str:
    if coverage is None:
        return "Low"
    if coverage >= 0.9:
        return "High"
    if coverage >= 0.6:
        return "Medium"
    return "Low"


def _metric(
    value: Any,
    currency: str | None,
    window: Window,
    sources: list[str],
    confidence: str,
    last_refresh: str,
    missing_data: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "value": value,
        "currency": currency,
        "window": window.to_dict(),
        "sources": sources,
        "last_refresh": last_refresh,
        "confidence": confidence,
        "missing_data": missing_data or [],
    }


def calculate_aov(net_sales: float, orders_count: int) -> float | None:
    if orders_count <= 0:
        return None
    return net_sales / orders_count


def calculate_upo(total_units: int, orders_count: int) -> float | None:
    if orders_count <= 0:
        return None
    return total_units / orders_count


def _customer_key(order: Order) -> str | None:
    if order.customer_id:
        return f"id:{order.customer_id}"
    if order.customer_email_hash:
        return f"email:{order.customer_email_hash}"
    return None


def _sales_quality_sources(orders: list[Order]) -> list[str]:
    sources = {order.source or "Shopify" for order in orders}
    return sorted(sources) if sources else ["Shopify"]


def get_sales_quality(db: Session, company_id: int, start: date, end: date) -> dict[str, Any]:
    company = db.query(Company).filter(Company.id == company_id).first()
    tz_name = company.timezone if company else "UTC"
    window = Window(start=start, end=end, timezone=tz_name)
    start_dt, end_dt = _window_bounds(window)
    last_refresh = datetime.now(timezone.utc).isoformat()

    orders = db.query(Order).filter(
        Order.company_id == company_id,
        Order.created_at >= start_dt,
        Order.created_at < end_dt,
    ).all()
    order_ids = [order.id for order in orders]
    order_lines = []
    if order_ids:
        order_lines = db.query(OrderLine).filter(
            OrderLine.order_id.in_(order_ids),
            OrderLine.company_id == company_id,
        ).all()

    orders_count = len(orders)
    net_sales = sum(order.net_sales or 0 for order in orders)
    total_units = sum(line.quantity or 0 for line in order_lines)
    total_line_sales = sum((line.unit_price or 0) * (line.quantity or 0) for line in order_lines)
    line_scale = (net_sales / total_line_sales) if total_line_sales > 0 else None
    sources = _sales_quality_sources(orders)

    base_confidence = "High" if orders_count > 0 else "Low"
    orders_metric = _metric(
        value=orders_count,
        currency=None,
        window=window,
        sources=sources,
        confidence=base_confidence,
        last_refresh=last_refresh,
        missing_data=["orders"] if orders_count == 0 else [],
    )
    net_sales_metric = _metric(
        value=round(net_sales, 2),
        currency=company.currency if company else None,
        window=window,
        sources=sources,
        confidence=base_confidence,
        last_refresh=last_refresh,
        missing_data=["orders"] if orders_count == 0 else [],
    )

    aov_value = calculate_aov(net_sales, orders_count)
    aov_metric = _metric(
        value=round(aov_value, 2) if aov_value is not None else None,
        currency=company.currency if company else None,
        window=window,
        sources=sources,
        confidence=base_confidence if aov_value is not None else "Low",
        last_refresh=last_refresh,
        missing_data=["orders"] if aov_value is None else [],
    )

    upo_value = calculate_upo(total_units, orders_count)
    upo_confidence = "High" if order_lines else "Low"
    upo_metric = _metric(
        value=round(upo_value, 2) if upo_value is not None else None,
        currency=None,
        window=window,
        sources=sources,
        confidence=upo_confidence,
        last_refresh=last_refresh,
        missing_data=["order_lines"] if not order_lines else [],
    )

    order_lines_confidence = "High" if order_lines else "Low"
    top_skus = []
    sku_totals: dict[str, dict[str, Any]] = defaultdict(lambda: {"net_sales": 0.0, "units": 0, "name": None, "product_type": None})
    for line in order_lines:
        raw_line_sales = (line.unit_price or 0) * (line.quantity or 0)
        scaled_line_sales = raw_line_sales * line_scale if line_scale is not None else raw_line_sales
        sku_totals[line.sku]["net_sales"] += scaled_line_sales
        sku_totals[line.sku]["units"] += line.quantity or 0
        sku_totals[line.sku]["name"] = line.product_name or sku_totals[line.sku]["name"] or "Unknown"
        sku_totals[line.sku]["product_type"] = line.product_type or sku_totals[line.sku]["product_type"]

    sorted_skus = sorted(sku_totals.items(), key=lambda item: item[1]["net_sales"], reverse=True)
    top_sku_sales = 0.0
    for sku, totals in sorted_skus[:10]:
        top_sku_sales += totals["net_sales"]
        share = (totals["net_sales"] / net_sales * 100) if net_sales > 0 else None
        top_skus.append(
            {
                "sku": sku,
                "product_name": totals["name"],
                "net_sales": _metric(
                    value=round(totals["net_sales"], 2),
                    currency=company.currency if company else None,
                    window=window,
                    sources=sources,
                    confidence=order_lines_confidence,
                    last_refresh=last_refresh,
                    missing_data=["order_lines"] if not order_lines else [],
                ),
                "units": _metric(
                    value=totals["units"],
                    currency=None,
                    window=window,
                    sources=sources,
                    confidence=order_lines_confidence,
                    last_refresh=last_refresh,
                    missing_data=["order_lines"] if not order_lines else [],
                ),
                "revenue_share_pct": _metric(
                    value=round(share, 2) if share is not None else None,
                    currency=None,
                    window=window,
                    sources=sources,
                    confidence=order_lines_confidence,
                    last_refresh=last_refresh,
                    missing_data=["orders", "order_lines"] if net_sales <= 0 else [],
                ),
            }
        )

    top10_share_value = (top_sku_sales / net_sales * 100) if net_sales > 0 and order_lines else None
    top10_share_metric = _metric(
        value=round(min(top10_share_value, 100.0), 2) if top10_share_value is not None else None,
        currency=None,
        window=window,
        sources=sources,
        confidence=order_lines_confidence,
        last_refresh=last_refresh,
        missing_data=["order_lines"] if not order_lines else [],
    )

    category_totals: dict[str, float] = defaultdict(float)
    has_category = False
    for line in order_lines:
        category = line.product_type or "Unknown"
        if line.product_type:
            has_category = True
        raw_line_sales = (line.unit_price or 0) * (line.quantity or 0)
        scaled_line_sales = raw_line_sales * line_scale if line_scale is not None else raw_line_sales
        category_totals[category] += scaled_line_sales

    categories = []
    if has_category:
        for category, total in sorted(category_totals.items(), key=lambda item: item[1], reverse=True):
            share = (total / net_sales * 100) if net_sales > 0 else None
            categories.append(
                {
                    "category": category,
                    "net_sales": _metric(
                        value=round(total, 2),
                        currency=company.currency if company else None,
                        window=window,
                        sources=sources,
                        confidence=order_lines_confidence,
                        last_refresh=last_refresh,
                        missing_data=["order_lines"] if not order_lines else [],
                    ),
                    "revenue_share_pct": _metric(
                        value=round(share, 2) if share is not None else None,
                        currency=None,
                        window=window,
                        sources=sources,
                        confidence=order_lines_confidence,
                        last_refresh=last_refresh,
                        missing_data=["orders", "order_lines"] if net_sales <= 0 else [],
                    ),
                }
            )

    channel_totals: dict[str, dict[str, float]] = defaultdict(lambda: {"net_sales": 0.0, "orders": 0})
    known_channel_orders = 0
    for order in orders:
        channel = order.sales_channel or "Unknown"
        channel_totals[channel]["net_sales"] += order.net_sales or 0
        channel_totals[channel]["orders"] += 1
        if channel != "Unknown":
            known_channel_orders += 1
    channel_coverage = known_channel_orders / orders_count if orders_count else None
    channel_confidence = _confidence_from_coverage(channel_coverage)
    channel_mix = []
    for channel, totals in sorted(channel_totals.items(), key=lambda item: item[1]["net_sales"], reverse=True):
        revenue_share = (totals["net_sales"] / net_sales * 100) if net_sales > 0 else None
        orders_share = (totals["orders"] / orders_count * 100) if orders_count > 0 else None
        channel_mix.append(
            {
                "channel": channel,
                "net_sales": _metric(
                    value=round(totals["net_sales"], 2),
                    currency=company.currency if company else None,
                    window=window,
                    sources=sources,
                    confidence=channel_confidence,
                    last_refresh=last_refresh,
                    missing_data=["source_name", "tags", "landing_site", "referring_site"] if channel_confidence == "Low" else [],
                ),
                "orders": _metric(
                    value=totals["orders"],
                    currency=None,
                    window=window,
                    sources=sources,
                    confidence=channel_confidence,
                    last_refresh=last_refresh,
                    missing_data=["source_name", "tags", "landing_site", "referring_site"] if channel_confidence == "Low" else [],
                ),
                "revenue_share_pct": _metric(
                    value=round(revenue_share, 2) if revenue_share is not None else None,
                    currency=None,
                    window=window,
                    sources=sources,
                    confidence=channel_confidence,
                    last_refresh=last_refresh,
                    missing_data=["orders"] if net_sales <= 0 else [],
                ),
                "orders_share_pct": _metric(
                    value=round(orders_share, 2) if orders_share is not None else None,
                    currency=None,
                    window=window,
                    sources=sources,
                    confidence=channel_confidence,
                    last_refresh=last_refresh,
                    missing_data=["orders"] if orders_count <= 0 else [],
                ),
            }
        )

    country_totals: dict[str, dict[str, float]] = defaultdict(lambda: {"net_sales": 0.0, "orders": 0})
    region_totals: dict[str, dict[str, float]] = defaultdict(lambda: {"net_sales": 0.0, "orders": 0})
    country_known = 0
    region_known = 0
    for order in orders:
        country = order.shipping_country or "Unknown"
        region = order.shipping_region or "Unknown"
        country_totals[country]["net_sales"] += order.net_sales or 0
        country_totals[country]["orders"] += 1
        region_totals[region]["net_sales"] += order.net_sales or 0
        region_totals[region]["orders"] += 1
        if order.shipping_country:
            country_known += 1
        if order.shipping_region:
            region_known += 1
    country_coverage = country_known / orders_count if orders_count else None
    region_coverage = region_known / orders_count if orders_count else None
    geo_confidence = _confidence_from_coverage(country_coverage)
    def _country_currency(country_value: str | None) -> str | None:
        if not country_value:
            return company.currency if company else None
        normalized = country_value.strip().lower()
        if normalized in {"us", "usa", "united states", "united states of america"}:
            return "USD"
        if normalized in {"united kingdom", "uk", "gb", "great britain"}:
            return "GBP"
        if normalized in {"germany", "de"}:
            return "EUR"
        return company.currency if company else None

    geo_mix_countries = []
    if orders_count > 0 and country_known > 0:
        for country, totals in sorted(country_totals.items(), key=lambda item: item[1]["net_sales"], reverse=True):
            country_currency = _country_currency(country)
            revenue_share = (totals["net_sales"] / net_sales * 100) if net_sales > 0 else None
            geo_mix_countries.append(
                {
                    "country": country,
                    "net_sales": _metric(
                        value=round(totals["net_sales"], 2),
                        currency=country_currency,
                        window=window,
                        sources=sources,
                        confidence=geo_confidence,
                        last_refresh=last_refresh,
                        missing_data=["shipping_country"] if geo_confidence == "Low" else [],
                    ),
                    "orders": _metric(
                        value=totals["orders"],
                        currency=None,
                        window=window,
                        sources=sources,
                        confidence=geo_confidence,
                        last_refresh=last_refresh,
                        missing_data=["shipping_country"] if geo_confidence == "Low" else [],
                    ),
                    "revenue_share_pct": _metric(
                        value=round(revenue_share, 2) if revenue_share is not None else None,
                        currency=None,
                        window=window,
                        sources=sources,
                        confidence=geo_confidence,
                        last_refresh=last_refresh,
                        missing_data=["orders"] if net_sales <= 0 else [],
                    ),
                }
            )

    geo_mix_regions = []
    if orders_count > 0 and region_known > 0:
        region_confidence = _confidence_from_coverage(region_coverage)
        for region, totals in sorted(region_totals.items(), key=lambda item: item[1]["net_sales"], reverse=True):
            revenue_share = (totals["net_sales"] / net_sales * 100) if net_sales > 0 else None
            geo_mix_regions.append(
                {
                    "region": region,
                    "net_sales": _metric(
                        value=round(totals["net_sales"], 2),
                        currency=company.currency if company else None,
                        window=window,
                        sources=sources,
                        confidence=region_confidence,
                        last_refresh=last_refresh,
                        missing_data=["shipping_region"] if region_confidence == "Low" else [],
                    ),
                    "orders": _metric(
                        value=totals["orders"],
                        currency=None,
                        window=window,
                        sources=sources,
                        confidence=region_confidence,
                        last_refresh=last_refresh,
                        missing_data=["shipping_region"] if region_confidence == "Low" else [],
                    ),
                    "revenue_share_pct": _metric(
                        value=round(revenue_share, 2) if revenue_share is not None else None,
                        currency=None,
                        window=window,
                        sources=sources,
                        confidence=region_confidence,
                        last_refresh=last_refresh,
                        missing_data=["orders"] if net_sales <= 0 else [],
                    ),
                }
            )

    currency_totals: dict[str, float] = defaultdict(float)
    currency_known = 0
    for order in orders:
        currency_code = order.currency_code
        if currency_code:
            currency_known += 1
            currency_totals[currency_code] += order.net_sales or 0
    currency_coverage = currency_known / orders_count if orders_count else None
    currency_confidence = _confidence_from_coverage(currency_coverage)
    currency_mix = []
    for currency_code, total in sorted(currency_totals.items(), key=lambda item: item[1], reverse=True):
        share = (total / net_sales * 100) if net_sales > 0 else None
        currency_mix.append(
            {
                "currency": currency_code,
                "net_sales": _metric(
                    value=round(total, 2),
                    currency=currency_code,
                    window=window,
                    sources=sources,
                    confidence=currency_confidence,
                    last_refresh=last_refresh,
                    missing_data=["currency_code"] if currency_confidence == "Low" else [],
                ),
                "revenue_share_pct": _metric(
                    value=round(share, 2) if share is not None else None,
                    currency=None,
                    window=window,
                    sources=sources,
                    confidence=currency_confidence,
                    last_refresh=last_refresh,
                    missing_data=["orders"] if net_sales <= 0 else [],
                ),
            }
        )

    fx_exposure = {"enabled": False, "top_non_base_currency": None, "share_pct": None}
    if company and len(currency_mix) > 1:
        non_base = [item for item in currency_mix if item["currency"] != company.currency]
        if non_base:
            top_non_base = max(non_base, key=lambda item: item["net_sales"]["value"] or 0)
            fx_exposure = {
                "enabled": True,
                "top_non_base_currency": top_non_base["currency"],
                "share_pct": top_non_base["revenue_share_pct"]["value"],
            }

    customers_in_window = []
    for order in orders:
        key = _customer_key(order)
        if key:
            customers_in_window.append(key)
    unique_customers_in_window = set(customers_in_window)
    customer_coverage = len(customers_in_window) / orders_count if orders_count else None
    customer_confidence = _confidence_from_coverage(customer_coverage)
    repeat_purchase_rate = None
    new_customer_orders = 0
    returning_customer_orders = 0
    new_customer_revenue = 0.0
    returning_customer_revenue = 0.0
    returning_customers = 0

    if unique_customers_in_window:
        all_customer_orders = db.query(Order).filter(
            Order.company_id == company_id,
            or_(Order.customer_id.isnot(None), Order.customer_email_hash.isnot(None)),
        ).all()
        first_order_dates: dict[str, datetime] = {}
        for order in all_customer_orders:
            key = _customer_key(order)
            if not key:
                continue
            first_order_dates[key] = min(first_order_dates.get(key, order.created_at), order.created_at)

        for order in orders:
            key = _customer_key(order)
            if not key:
                continue
            first_order = first_order_dates.get(key)
            if first_order and start_dt <= first_order < end_dt:
                new_customer_orders += 1
                new_customer_revenue += order.net_sales or 0
            else:
                returning_customer_orders += 1
                returning_customer_revenue += order.net_sales or 0

        for customer in unique_customers_in_window:
            first_order = first_order_dates.get(customer)
            if first_order and first_order < start_dt:
                returning_customers += 1

        total_customers = len(unique_customers_in_window)
        repeat_purchase_rate = (returning_customers / total_customers * 100) if total_customers > 0 else None

    total_revenue = new_customer_revenue + returning_customer_revenue
    new_rev_pct = (new_customer_revenue / total_revenue * 100) if total_revenue > 0 else None
    returning_rev_pct = (returning_customer_revenue / total_revenue * 100) if total_revenue > 0 else None

    repeat_metric = _metric(
        value=round(repeat_purchase_rate, 2) if repeat_purchase_rate is not None else None,
        currency=None,
        window=window,
        sources=sources,
        confidence=customer_confidence,
        last_refresh=last_refresh,
        missing_data=["customer_id", "customer_email_hash"] if customer_confidence == "Low" else [],
    )

    new_vs_returning = {
        "new_customer_revenue": _metric(
            value=round(new_customer_revenue, 2) if unique_customers_in_window else None,
            currency=company.currency if company else None,
            window=window,
            sources=sources,
            confidence=customer_confidence,
            last_refresh=last_refresh,
            missing_data=["customer_id", "customer_email_hash"] if customer_confidence == "Low" else [],
        ),
        "returning_customer_revenue": _metric(
            value=round(returning_customer_revenue, 2) if unique_customers_in_window else None,
            currency=company.currency if company else None,
            window=window,
            sources=sources,
            confidence=customer_confidence,
            last_refresh=last_refresh,
            missing_data=["customer_id", "customer_email_hash"] if customer_confidence == "Low" else [],
        ),
        "new_customer_revenue_pct": _metric(
            value=round(new_rev_pct, 2) if new_rev_pct is not None else None,
            currency=None,
            window=window,
            sources=sources,
            confidence=customer_confidence,
            last_refresh=last_refresh,
            missing_data=["customer_id", "customer_email_hash"] if customer_confidence == "Low" else [],
        ),
        "returning_customer_revenue_pct": _metric(
            value=round(returning_rev_pct, 2) if returning_rev_pct is not None else None,
            currency=None,
            window=window,
            sources=sources,
            confidence=customer_confidence,
            last_refresh=last_refresh,
            missing_data=["customer_id", "customer_email_hash"] if customer_confidence == "Low" else [],
        ),
        "new_customer_orders": _metric(
            value=new_customer_orders if unique_customers_in_window else None,
            currency=None,
            window=window,
            sources=sources,
            confidence=customer_confidence,
            last_refresh=last_refresh,
            missing_data=["customer_id", "customer_email_hash"] if customer_confidence == "Low" else [],
        ),
        "returning_customer_orders": _metric(
            value=returning_customer_orders if unique_customers_in_window else None,
            currency=None,
            window=window,
            sources=sources,
            confidence=customer_confidence,
            last_refresh=last_refresh,
            missing_data=["customer_id", "customer_email_hash"] if customer_confidence == "Low" else [],
        ),
        "repeat_purchase_rate": repeat_metric,
    }

    kpis = {
        "orders_count": orders_metric,
        "net_sales": net_sales_metric,
        "aov": aov_metric,
        "upo": upo_metric,
        "repeat_purchase_rate": repeat_metric,
        "top10_sku_share": top10_share_metric,
    }

    overall_confidence = min(
        {orders_metric["confidence"], aov_metric["confidence"], upo_metric["confidence"], channel_confidence, geo_confidence, currency_confidence},
        key=lambda item: {"High": 3, "Medium": 2, "Low": 1}.get(item, 1),
    )

    return {
        "kpis": kpis,
        "new_vs_returning": new_vs_returning,
        "top_skus": top_skus,
        "categories": categories,
        "channel_mix": channel_mix,
        "geo_mix": {
            "countries": geo_mix_countries,
            "regions": geo_mix_regions,
            "confidence": geo_confidence,
            "missing_data": ["shipping_country"] if geo_confidence == "Low" else [],
        },
        "currency_mix": {
            "items": currency_mix,
            "confidence": currency_confidence,
            "missing_data": ["currency_code"] if currency_confidence == "Low" else [],
            "fx_exposure": fx_exposure,
        },
        "metadata": {
            "sources": sources,
            "last_refresh": last_refresh,
            "confidence": overall_confidence,
            "window": window.to_dict(),
        },
    }
