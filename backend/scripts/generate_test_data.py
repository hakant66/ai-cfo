import os
import random
import time
import shopify


SHOP_URL = os.getenv("SHOPIFY_SHOP_URL")
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-01")
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
ORDERS_COUNT = int(os.getenv("SHOPIFY_ORDERS_COUNT", "10"))
REFUND_COUNT = int(os.getenv("SHOPIFY_REFUND_COUNT", "3"))
PRODUCT_SEED_COUNT = int(os.getenv("SHOPIFY_PRODUCT_SEED_COUNT", "5"))


def seed_products(count: int) -> None:
    print(f"--- Seeding {count} Products ---")
    for i in range(count):
        product = shopify.Product()
        product.title = f"CFO Test Product {i + 1}"
        product.vendor = "AI CFO"
        product.product_type = "Demo"
        product.tags = "demo,cfo"
        product.variants = [
            {
                "price": str(round(random.uniform(20.0, 150.0), 2)),
                "sku": f"CFO-DEMO-{i + 1}",
                "inventory_management": "shopify",
                "inventory_quantity": random.randint(5, 50),
            }
        ]
        if product.save():
            print(f"Product created (ID: {product.id})")
        else:
            print(f"Failed to create product: {product.errors.full_messages()}")


def create_mock_orders(count: int) -> list[int]:
    created_order_ids = []
    print(f"--- Creating {count} Mock Orders ---")

    products = shopify.Product.find(limit=5)
    if not products:
        print("No products found. Creating demo products.")
        seed_products(PRODUCT_SEED_COUNT)
        products = shopify.Product.find(limit=5)
        if not products:
            print("Error: No products found after seeding.")
            return []

    variant = products[0].variants[0]

    for i in range(count):
        order = shopify.Order()
        order.line_items = [
            {
                "variant_id": variant.id,
                "quantity": random.randint(1, 3),
                "price": str(round(random.uniform(20.0, 150.0), 2)),
            }
        ]
        order.email = f"customer_{i}@example.com"
        order.financial_status = "paid"

        if order.save():
            print(f"Order #{order.name} created (ID: {order.id})")
            created_order_ids.append(order.id)
        else:
            print(f"Failed to create order {i}: {order.errors.full_messages()}")

    return created_order_ids


def refund_orders(order_ids: list[int], count: int = 3) -> None:
    print(f"\n--- Refunding {count} Orders ---")
    to_refund = random.sample(order_ids, min(count, len(order_ids)))

    for order_id in to_refund:
        order = shopify.Order.find(order_id)

        refund_line_items = []
        for item in order.line_items:
            refund_line_items.append(
                {
                    "line_item_id": item.id,
                    "quantity": item.quantity,
                    "restock_type": "no_restock",
                }
            )

        refund = shopify.Refund(
            {
                "order_id": order.id,
                "refund_line_items": refund_line_items,
                "note": "CFO Test: Customer returned item",
                "notify": False,
                "currency": order.currency,
            }
        )

        transactions = order.transactions()
        refund.transactions = [
            {
                "parent_id": transactions[0].id if transactions else None,
                "amount": order.total_price,
                "kind": "refund",
                "gateway": "bogus",
            }
        ]

        if refund.save():
            print(f"Successfully refunded Order ID: {order_id}")
        else:
            print(f"Failed to refund {order_id}: {refund.errors.full_messages()}")


if __name__ == "__main__":
    if not SHOP_URL or not ACCESS_TOKEN:
        raise SystemExit("Set SHOPIFY_SHOP_URL and SHOPIFY_ACCESS_TOKEN before running.")

    session = shopify.Session(SHOP_URL, API_VERSION, ACCESS_TOKEN)
    shopify.ShopifyResource.activate_session(session)

    order_list = create_mock_orders(ORDERS_COUNT)
    if order_list:
        time.sleep(2)
        refund_orders(order_list, REFUND_COUNT)

    print("\nData generation complete.")