import requests
import sqlite3  # Replace with your actual DB connector

# Database functions
def get_product_from_db(product_id):
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, supplier_price, selling_price, supplier_api_url FROM products WHERE id=?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "name": row[1],
            "supplier_price": row[2],
            "selling_price": row[3],
            "supplier_api_url": row[4]
        }
    else:
        raise Exception("Product not found")

def save_order(order_data):
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (product_id, quantity, buyer_country, buyer_region, buyer_city, buyer_postal, supplier_price, shipping_cost, selling_price, profit)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order_data["product_id"],
        order_data["quantity"],
        order_data["buyer_address"]["country"],
        order_data["buyer_address"]["region"],
        order_data["buyer_address"]["city"],
        order_data["buyer_address"]["postal_code"],
        order_data["supplier_price"],
        order_data["shipping_cost"],
        order_data["selling_price"],
        order_data["profit"]
    ))
    conn.commit()
    order_id = cursor.lastrowid
    conn.close()
    return order_id

def update_profit(product_id, profit):
    conn = sqlite3.connect("store.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET total_profit = total_profit + ? WHERE id=?", (profit, product_id))
    conn.commit()
    conn.close()

# Core function
def checkout_product(product_id, quantity, buyer_address):
    product = get_product_from_db(product_id)
    supplier_price = product["supplier_price"]
    selling_price = product["selling_price"]
    supplier_api = product["supplier_api_url"]

    # Ask supplier for shipping
    response = requests.post(
        f"{supplier_api}/get_shipping",
        json={
            "product_id": product_id,
            "quantity": quantity,
            "destination": buyer_address
        },
        timeout=10
    )
    response.raise_for_status()
    shipping_cost = response.json().get("shipping_price")
    if shipping_cost is None:
        raise Exception("Supplier did not return shipping cost")

    # Calculate totals
    total_price = selling_price * quantity + shipping_cost
    profit = selling_price * quantity - (supplier_price * quantity + shipping_cost)

    # Save order & update profit
    order_data = {
        "product_id": product_id,
        "quantity": quantity,
        "buyer_address": buyer_address,
        "supplier_price": supplier_price,
        "shipping_cost": shipping_cost,
        "selling_price": selling_price,
        "profit": profit
    }
    order_id = save_order(order_data)
    update_profit(product_id, profit)

    # Return structured info for frontend
    return {
        "order_id": order_id,
        "product_price": selling_price * quantity,
        "shipping_cost": shipping_cost,
        "total_price": total_price,
        "profit": profit
    }

# Example usage
if __name__ == "__main__":
    buyer_address = {
        "country": "Russia",
        "region": "Moscow",
        "city": "Moscow",
        "postal_code": "101000"
    }
    result = checkout_product(product_id=1234, quantity=2, buyer_address=buyer_address)
    print(result)
