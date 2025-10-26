import uuid

class InvoicePayment:
    def __init__(self, nocodb):
        self.nocodb = nocodb

    def generate_invoices(self):
        print("🧾 Generating invoices for completed orders...")
        orders = self.nocodb.get_table("project_store", "orders")
        for o in orders.get("list", []):
            if o.get("status") == "completed" and not o.get("invoice_id"):
                invoice_id = str(uuid.uuid4())
                print(f"Creating invoice {invoice_id} for order {o['id']}")
                self.nocodb.insert_record("project_store", "invoices", {
                    "order_id": o['id'],
                    "invoice_number": invoice_id,
                    "amount": o.get("total_price", 0),
                    "status": "unpaid"
                })
