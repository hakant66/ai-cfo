import requests
from datetime import datetime
from typing import Optional
from app.core.config import settings


def _normalize_base_url(shop_domain: Optional[str]) -> str:
    if settings.shopify_url:
        base = settings.shopify_url
    else:
        if not shop_domain:
            raise ValueError("shop_domain or SHOPIFY_URL must be provided")
        base = shop_domain

    if base.startswith("http://") or base.startswith("https://"):
        return base.rstrip("/")
    if "mock-shopify" in base:
        return f"http://{base}".rstrip("/")
    return f"https://{base}".rstrip("/")


def _graphql_url(base_url: str) -> str:
    if base_url.endswith("/graphql") or base_url.endswith("/graphql.json"):
        return base_url
    if base_url.endswith("/admin/api/2023-10"):
        return f"{base_url}/graphql.json"
    return f"{base_url}/graphql"


def _access_token(access_token: Optional[str]) -> str:
    return access_token or settings.shopify_access_token or ""


def _should_use_graphql(shop_domain: Optional[str]) -> bool:
    base_url = _normalize_base_url(shop_domain)
    return settings.shopify_use_graphql or "mock-shopify" in base_url


def test_connection(shop_domain: str, access_token: str) -> dict:
    base_url = _normalize_base_url(shop_domain)
    use_graphql = settings.shopify_use_graphql or "mock-shopify" in base_url
    if use_graphql:
        url = _graphql_url(base_url)
        query = "{ products(first: 1) { edges { node { id title } } } }"
        response = requests.post(
            url,
            json={"query": query},
            headers={"X-Shopify-Access-Token": _access_token(access_token)},
            timeout=30,
        )
        if response.status_code != 200:
            return {"ok": False, "status": response.status_code, "body": response.text}
        payload = response.json()
        if payload.get("errors"):
            return {"ok": False, "status": 400, "body": payload.get("errors")}
        return {"ok": True, "mode": "graphql"}

    url = f"{base_url}/admin/api/2023-10/shop.json" if "/admin/api" not in base_url else f"{base_url}/shop.json"
    response = requests.get(url, headers={"X-Shopify-Access-Token": _access_token(access_token)}, timeout=30)
    if response.status_code != 200:
        return {"ok": False, "status": response.status_code, "body": response.text}
    return {"ok": True, "mode": "rest", "shop": response.json().get("shop", {})}


def fetch_orders_graphql(shop_domain: Optional[str], access_token: Optional[str]) -> list[dict]:
    base_url = _normalize_base_url(shop_domain)
    url = _graphql_url(base_url)
    query = """
    query {
      orders(first: 20) {
        edges {
          node {
            id
            createdAt
            totalPriceSet { shopMoney { amount currencyCode } }
            totalDiscountsSet { shopMoney { amount currencyCode } }
            currencyCode
            sourceName
            app { id name }
            tags
            landingSite
            referringSite
            customer { id email }
            shippingAddress {
              country
              countryCode
              province
              provinceCode
            }
            lineItems(first: 50) {
              edges {
                node {
                  title
                  quantity
                  sku
                  product { productType }
                  originalUnitPriceSet { shopMoney { amount currencyCode } }
                }
              }
            }
            refunds(first: 20) {
              edges {
                node {
                  id
                  createdAt
                  totalRefundedSet { shopMoney { amount currencyCode } }
                  refundLineItems(first: 20) {
                    edges {
                      node {
                        quantity
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    response = requests.post(
        url,
        json={"query": query},
        headers={"X-Shopify-Access-Token": _access_token(access_token)},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    orders = []
    for edge in payload.get("data", {}).get("orders", {}).get("edges", []):
        node = edge.get("node", {})
        total_price = float(node.get("totalPriceSet", {}).get("shopMoney", {}).get("amount", 0) or 0)
        discounts = float(node.get("totalDiscountsSet", {}).get("shopMoney", {}).get("amount", 0) or 0)
        currency_code = node.get("currencyCode") or node.get("totalPriceSet", {}).get("shopMoney", {}).get("currencyCode")
        refunds = []
        for refund_edge in node.get("refunds", {}).get("edges", []):
            refund_node = refund_edge.get("node", {})
            amount = float(refund_node.get("totalRefundedSet", {}).get("shopMoney", {}).get("amount", 0) or 0)
            quantity = 0
            for line_edge in refund_node.get("refundLineItems", {}).get("edges", []):
                quantity += int(line_edge.get("node", {}).get("quantity", 0) or 0)
            refunds.append(
                {
                    "id": refund_node.get("id"),
                    "created_at": refund_node.get("createdAt"),
                    "amount": amount,
                    "quantity": quantity,
                }
            )
        line_items = []
        for line_edge in node.get("lineItems", {}).get("edges", []):
            line_node = line_edge.get("node", {})
            unit_price = float(line_node.get("originalUnitPriceSet", {}).get("shopMoney", {}).get("amount", 0) or 0)
            line_items.append(
                {
                    "sku": line_node.get("sku"),
                    "quantity": int(line_node.get("quantity") or 0),
                    "price": unit_price,
                    "title": line_node.get("title"),
                    "product_type": line_node.get("product", {}).get("productType"),
                }
            )
        orders.append(
            {
                "id": node.get("id"),
                "total_price": total_price,
                "total_discounts": discounts,
                "created_at": node.get("createdAt"),
                "currency": currency_code,
                "source_name": node.get("sourceName"),
                "app_id": node.get("app", {}).get("id"),
                "landing_site": node.get("landingSite"),
                "referring_site": node.get("referringSite"),
                "tags": ", ".join(node.get("tags") or []),
                "customer": node.get("customer") or {},
                "shipping_address": node.get("shippingAddress") or {},
                "line_items": line_items,
                "refunds": refunds,
            }
        )
    return orders


def fetch_orders(shop_domain: Optional[str], access_token: Optional[str], since: datetime | None = None) -> list[dict]:
    if _should_use_graphql(shop_domain):
        return fetch_orders_graphql(shop_domain, access_token)
    base_url = _normalize_base_url(shop_domain)
    params = {"status": "any", "limit": 50}
    if since:
        params["created_at_min"] = since.isoformat()
    url = f"{base_url}/admin/api/2023-10/orders.json" if "/admin/api" not in base_url else f"{base_url}/orders.json"
    response = requests.get(url, headers={"X-Shopify-Access-Token": _access_token(access_token)}, params=params, timeout=30)
    response.raise_for_status()
    return response.json().get("orders", [])


def fetch_inventory_graphql(shop_domain: Optional[str], access_token: Optional[str]) -> list[dict]:
    base_url = _normalize_base_url(shop_domain)
    url = _graphql_url(base_url)
    query = """
    query {
      inventoryLevels(first: 20) {
        edges {
          node {
            available
            inventoryItem { id }
          }
        }
      }
    }
    """
    response = requests.post(
        url,
        json={"query": query},
        headers={"X-Shopify-Access-Token": _access_token(access_token)},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    items = []
    for edge in payload.get("data", {}).get("inventoryLevels", {}).get("edges", []):
        node = edge.get("node", {})
        items.append(
            {
                "inventory_item_id": node.get("inventoryItem", {}).get("id"),
                "available": node.get("available", 0),
            }
        )
    return items


def fetch_inventory(shop_domain: Optional[str], access_token: Optional[str]) -> list[dict]:
    if _should_use_graphql(shop_domain):
        return fetch_inventory_graphql(shop_domain, access_token)
    base_url = _normalize_base_url(shop_domain)
    url = f"{base_url}/admin/api/2023-10/inventory_levels.json" if "/admin/api" not in base_url else f"{base_url}/inventory_levels.json"
    response = requests.get(url, headers={"X-Shopify-Access-Token": _access_token(access_token)}, timeout=30)
    response.raise_for_status()
    return response.json().get("inventory_levels", [])


def fetch_products_graphql(shop_domain: Optional[str], access_token: Optional[str]) -> list[dict]:
    base_url = _normalize_base_url(shop_domain)
    url = _graphql_url(base_url)
    query = """
    query {
      products(first: 20) {
        edges {
          node {
            id
            title
            handle
            vendor
          }
        }
      }
    }
    """
    response = requests.post(
        url,
        json={"query": query},
        headers={"X-Shopify-Access-Token": _access_token(access_token)},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    products = []
    for edge in payload.get("data", {}).get("products", {}).get("edges", []):
        node = edge.get("node", {})
        products.append(
            {
                "id": node.get("id"),
                "title": node.get("title"),
                "handle": node.get("handle"),
                "vendor": node.get("vendor"),
            }
        )
    return products


def fetch_products(shop_domain: Optional[str], access_token: Optional[str]) -> list[dict]:
    if _should_use_graphql(shop_domain):
        return fetch_products_graphql(shop_domain, access_token)
    base_url = _normalize_base_url(shop_domain)
    url = f"{base_url}/admin/api/2023-10/products.json" if "/admin/api" not in base_url else f"{base_url}/products.json"
    response = requests.get(url, headers={"X-Shopify-Access-Token": _access_token(access_token)}, timeout=30)
    response.raise_for_status()
    return response.json().get("products", [])
