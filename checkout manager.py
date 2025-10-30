import os
import requests
from database import (
    get_product_from_db,
    save_order,
    update_profit,
    flag_suspicious_activity,
    freeze_account,
    get_supplier_info,
    record_supplier_payment
)
from ai_fraud_detection import detect_suspicious_activity

# Environment variables from Vercel
STRIPE_KEY = os.getenv("STRIPE_KEY")
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")

# Placeholder payment modules; replace with actual SDK imports
import stripe
import paypalrestsdk

stripe.api_key = STRIPE_KEY
paypalrestsdk.configure({
    "mode": "live",
    "client_id": PAYPAL_CLIENT_ID,
    "client_secret": PAYPAL_CLIENT_SECRET
})


def process_order(customer, product_id, quantity, buyer_address):
    """
    Full AI-driven dropshipping workflow
    """
    # 1. Get product info
    product = get_product_from_db(product_id)
    supplier_api = product["supplier_api_url"]
    supplier_price = product["supplier_price"]
    selling_price = product["selling_price"]

    # 2. Query supplier for shipping cost
    try:
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
            raise ValueError("Supplier did not return shipping cost")
    except Exception as e:
        return {"status": "error", "message": f"Shipping lookup failed: {e}"}

    # 3. Calculate total and profit
    product_total = selling_price * quantity
    total_price = product_total + shipping_cost
    profit = product_total - (supplier_price * quantity + shipping_cost)

    # 4. Fraud / suspicious activity check
    if detect_suspicious_activity(customer, product_id, quantity, buyer_address):
        flag_suspicious_activity(customer["id"], product_id)
        freeze_account(customer["id"])
        return {
            "status": "suspicious",
            "message": "Account temporarily frozen due to suspicious activity"
        }

    # 5. Capture customer payment
    payment_status = None
    try:
        if customer["payment_method"] == "stripe":
            payment_intent = stripe.PaymentIntent.create(
                amount=int(total_price * 100),
                currency="usd",
                payment_method=customer["stripe_payment_method"],
                confirm=True
            )
            payment_status = payment_intent["status"]
        else:  # PayPal
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {"payment_method": "paypal"},
                "transactions": [{"amount": {"total": f"{total_price:.2f}", "currency": "USD"}}],
                "redirect_urls": {"return_url": "https://yourstore.com/success",
                                  "cancel_url": "https://yourstore.com/cancel"}
            })
            if payment.create():
                payment_status = "approved"
            else:
                payment_status = "failed"
    except Exception as e:
        return {"status": "error", "message": f"Payment failed: {e}"}

    if payment_status not in ["succeeded", "approved"]:
        return {"status": "failed", "message": "Payment could not be processed"}

    # 6. Pay supplier
    supplier = get_supplier_info(product["supplier_id"])
    supplier_amount = supplier_price * quantity + shipping_cost

    try:
        if supplier["payment_method"] == "paypal":
            payout = paypalrestsdk.Payout({
                "sender_batch_header": {
                    "sender_batch_id": f"batch_{product_id}_{customer['id']}",
                    "email_subject": "You have a payment"
                },
                "items": [{
                    "recipient_type": "EMAIL",
                    "amount": {"value": f"{supplier_amount:.2f}", "currency": "USD"},
                    "receiver": supplier["paypal_email"],
                    "note": "Supplier payment"
                }]
            })
            payout.create(sync_mode=True)
        elif supplier["payment_method"] == "stripe":
            import stripe
            stripe.Transfer.create(
                amount=int(supplier_amount * 100),
                currency="usd",
                destination=supplier["stripe_account_id"]
            )
        record_supplier_payment(supplier["id"], supplier_amount)
    except Exception as e:
        # Optional: retry logic or mark for manual intervention
        return {"status": "error", "message": f"Supplier payment failed: {e}"}

    # 7. Save order and profit
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

    # 8. Return structured info for frontend
    return {
        "status": "success",
        "order_id": order_id,
        "product_price": product_total,
        "shipping_cost": shipping_cost,
        "total_price": total_price,
        "profit": profit
    }

