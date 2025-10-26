class StoreManager:
    def __init__(self, nocodb):
        self.nocodb = nocodb

    def sync_inventory(self):
        print("🛒 Syncing product inventory with NocoDB...")
        # Example logic to sync local & online inventory
        products = self.nocodb.get_table("project_store", "products")
        print(f"Fetched {len(products)} products.")

    def process_orders(self):
        print("📦 Checking new orders...")
        orders = self.nocodb.get_table("project_store", "orders")
        for o in orders.get("list", []):
            if o.get("status") == "pending":
                print(f"Processing order {o['id']} for {o['customer_name']}")
                self.nocodb.update_record("project_store", "orders", o['id'], {"status": "completed"})
