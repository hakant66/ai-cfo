from datetime import datetime, timedelta
from fastapi import FastAPI, Request

app = FastAPI()

PRODUCTS = [
    {
        "id": "gid://shopify/Product/1001",
        "title": "Canvas Utility Tote",
        "handle": "canvas-utility-tote",
        "vendor": "Dockside Co",
        "product_type": "Bags",
        "inventory_item_id": "gid://shopify/InventoryItem/5001",
        "available": 42,
    },
    {
        "id": "gid://shopify/Product/1002",
        "title": "Ceramic Travel Mug",
        "handle": "ceramic-travel-mug",
        "vendor": "Northwind",
        "product_type": "Drinkware",
        "inventory_item_id": "gid://shopify/InventoryItem/5002",
        "available": 18,
    },
    {
        "id": "gid://shopify/Product/1003",
        "title": "Wool Blend Throw",
        "handle": "wool-blend-throw",
        "vendor": "Harbor Mills",
        "product_type": "Home",
        "inventory_item_id": "gid://shopify/InventoryItem/5003",
        "available": 7,
    },
    {
        "id": "gid://shopify/Product/1004",
        "title": "Marina Ring",
        "handle": "marina-ring",
        "vendor": "Drift & Gold",
        "product_type": "Ring",
        "inventory_item_id": "gid://shopify/InventoryItem/5004",
        "available": 12,
    },
    {
        "id": "gid://shopify/Product/1005",
        "title": "Crescent Bracelet",
        "handle": "crescent-bracelet",
        "vendor": "Drift & Gold",
        "product_type": "Bracelet",
        "inventory_item_id": "gid://shopify/InventoryItem/5005",
        "available": 16,
    },
    {
        "id": "gid://shopify/Product/1006",
        "title": "Harbor Earrings",
        "handle": "harbor-earrings",
        "vendor": "Drift & Gold",
        "product_type": "Earrings",
        "inventory_item_id": "gid://shopify/InventoryItem/5006",
        "available": 24,
    },
    {
        "id": "gid://shopify/Product/1007",
        "title": "Tide Necklace",
        "handle": "tide-necklace",
        "vendor": "Drift & Gold",
        "product_type": "Necklace",
        "inventory_item_id": "gid://shopify/InventoryItem/5007",
        "available": 9,
    },
]

def build_orders():
    base_time = datetime.utcnow() - timedelta(hours=2)
    line_items = [
        {
            "title": PRODUCTS[0]["title"],
            "sku": "SKU-1001",
            "quantity": 2,
            "price": 220.00,
            "product_type": PRODUCTS[0]["product_type"],
        },
        {
            "title": PRODUCTS[1]["title"],
            "sku": "SKU-1002",
            "quantity": 1,
            "price": 140.00,
            "product_type": PRODUCTS[1]["product_type"],
        },
    ]
    jewelry_items = [
        {
            "title": PRODUCTS[3]["title"],
            "sku": "SKU-1004",
            "quantity": 1,
            "price": 95.00,
            "product_type": PRODUCTS[3]["product_type"],
        },
        {
            "title": PRODUCTS[4]["title"],
            "sku": "SKU-1005",
            "quantity": 1,
            "price": 110.00,
            "product_type": PRODUCTS[4]["product_type"],
        },
        {
            "title": PRODUCTS[5]["title"],
            "sku": "SKU-1006",
            "quantity": 1,
            "price": 75.00,
            "product_type": PRODUCTS[5]["product_type"],
        },
        {
            "title": PRODUCTS[6]["title"],
            "sku": "SKU-1007",
            "quantity": 1,
            "price": 220.00,
            "product_type": PRODUCTS[6]["product_type"],
        },
    ]
    return [
        {
            "id": "gid://shopify/Order/1999",
            "created_at": (base_time - timedelta(days=3)).isoformat() + "Z",
            "total_price": 300.00,
            "total_discounts": 0.00,
            "currency": "USD",
            "source_name": "web",
            "tags": "vip",
            "landing_site": "https://example.com/spring",
            "referring_site": "https://google.com",
            "customer": {"id": "gid://shopify/Customer/9001", "email": "buyer1@example.com"},
            "shipping_address": {"country": "United States", "country_code": "US", "province": "Los Angelos", "province_code": "LAX"},
            "line_items": [jewelry_items[0]],
            "refunds": [],
        },
        {
            "id": "gid://shopify/Order/2001",
            "created_at": base_time.isoformat() + "Z",
            "total_price": 220.00,
            "total_discounts": 0.00,
            "currency": "USD",
            "source_name": "web",
            "tags": "vip,repeat",
            "landing_site": "https://example.com/spring",
            "referring_site": "https://google.com",
            "customer": {"id": "gid://shopify/Customer/9001", "email": "buyer1@example.com"},
            "shipping_address": {"country": "United States", "country_code": "US", "province": "Los Angelos", "province_code": "LAX"},
            "line_items": [jewelry_items[0]],
            "refunds": [
                {
                    "id": "gid://shopify/Refund/3001",
                    "created_at": (base_time + timedelta(hours=5)).isoformat() + "Z",
                    "amount": 20.00,
                    "quantity": 1,
                }
            ],
        },
        {
            "id": "gid://shopify/Order/2002",
            "created_at": (base_time + timedelta(hours=2)).isoformat() + "Z",
            "total_price": 420.00,
            "total_discounts": 0.00,
            "currency": "GBP",
            "source_name": "web",
            "tags": "new",
            "landing_site": "https://example.com/landing",
            "referring_site": "https://instagram.com",
            "customer": {"id": "gid://shopify/Customer/9002", "email": "buyer2@example.com"},
            "shipping_address": {"country": "United Kingdom", "country_code": "GB", "province": "London", "province_code": "LON"},
            "line_items": [line_items[0], jewelry_items[1]],
            "refunds": [],
        },
        {
            "id": "gid://shopify/Order/2003",
            "created_at": (base_time + timedelta(hours=3)).isoformat() + "Z",
            "total_price": 380.00,
            "total_discounts": 15.00,
            "currency": "EUR",
            "source_name": "web",
            "tags": "wholesale",
            "landing_site": "https://example.com/wholesale",
            "referring_site": "https://partner.example.com",
            "customer": {"id": "gid://shopify/Customer/9003", "email": "buyer3@example.com"},
            "shipping_address": {"country": "Germany", "country_code": "DE", "province": "Berlin", "province_code": "BER"},
            "line_items": [line_items[0], jewelry_items[2]],
            "refunds": [
                {
                    "id": "gid://shopify/Refund/3002",
                    "created_at": (base_time + timedelta(hours=8)).isoformat() + "Z",
                    "amount": 30.00,
                    "quantity": 2,
                }
            ],
        },
        {
            "id": "gid://shopify/Order/2004",
            "created_at": (base_time + timedelta(hours=6)).isoformat() + "Z",
            "total_price": 300.00,
            "total_discounts": 0.00,
            "currency": "EUR",
            "source_name": "web",
            "tags": "marketplace,amazon",
            "landing_site": "https://amazon.com",
            "referring_site": "https://amazon.com",
            "customer": {"id": "gid://shopify/Customer/9004", "email": "buyer4@example.com"},
            "shipping_address": {"country": "United States", "country_code": "US", "province": "Austin", "province_code": "AUS"},
            "line_items": [jewelry_items[3]],
            "refunds": [],
        },
    ]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/graphql")
async def graphql(request: Request):
    payload = await request.json()
    query = (payload.get("query") or "").lower()

    if "products" in query:
        return {
            "data": {
                "products": {
                    "edges": [
                        {"node": {"id": item["id"], "title": item["title"], "handle": item["handle"], "vendor": item["vendor"]}}
                        for item in PRODUCTS
                    ]
                }
            }
        }

    if "inventorylevels" in query:
        return {
            "data": {
                "inventoryLevels": {
                    "edges": [
                        {
                            "node": {
                                "available": item["available"],
                                "inventoryItem": {"id": item["inventory_item_id"]},
                            }
                        }
                        for item in PRODUCTS
                    ]
                }
            }
        }

    if "orders" in query:
        orders = build_orders()
        return {
            "data": {
                "orders": {
                    "edges": [
                        {
                            "node": {
                                "id": order["id"],
                                "createdAt": order["created_at"],
                                "totalPriceSet": {"shopMoney": {"amount": f"{order['total_price']:.2f}", "currencyCode": "USD"}},
                                "totalDiscountsSet": {"shopMoney": {"amount": f"{order['total_discounts']:.2f}", "currencyCode": "USD"}},
                                "currencyCode": order["currency"],
                                "sourceName": order["source_name"],
                                "app": {"id": "gid://shopify/App/1", "name": "Mock App"},
                                "tags": [tag.strip() for tag in order["tags"].split(",") if tag.strip()],
                                "landingSite": order["landing_site"],
                                "referringSite": order["referring_site"],
                                "customer": {"id": order["customer"]["id"], "email": order["customer"]["email"]},
                                "shippingAddress": {
                                    "country": order["shipping_address"]["country"],
                                    "countryCode": order["shipping_address"]["country_code"],
                                    "province": order["shipping_address"]["province"],
                                    "provinceCode": order["shipping_address"]["province_code"],
                                },
                                "lineItems": {
                                    "edges": [
                                        {
                                            "node": {
                                                "title": item["title"],
                                                "quantity": item["quantity"],
                                                "sku": item["sku"],
                                                "product": {"productType": item["product_type"]},
                                                "originalUnitPriceSet": {
                                                    "shopMoney": {"amount": f"{item['price']:.2f}", "currencyCode": "USD"}
                                                },
                                            }
                                        }
                                        for item in order["line_items"]
                                    ]
                                },
                                "refunds": {
                                    "edges": [
                                        {
                                            "node": {
                                                "id": refund["id"],
                                                "createdAt": refund["created_at"],
                                                "totalRefundedSet": {
                                                    "shopMoney": {"amount": f"{refund['amount']:.2f}", "currencyCode": "USD"}
                                                },
                                                "refundLineItems": {
                                                    "edges": [
                                                        {"node": {"quantity": refund["quantity"]}}
                                                    ]
                                                },
                                            }
                                        }
                                        for refund in order["refunds"]
                                    ]
                                },
                            }
                        }
                        for order in orders
                    ]
                }
            }
        }

    return {"data": {}}
