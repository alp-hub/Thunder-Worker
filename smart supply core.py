# smart_supply_core.py
"""
Smart Supply Core
- Monitors suppliers for stock & price
- Fetches competitor prices
- Calculates a selling price 2% lower than competitor average
- Ensures minimum profit margin and updates store DB / external store API
- Intended to be run periodically (cron, serverless job, or background worker)

Environment variables expected:
- SUPPLIER_<N>_API_KEY and SUPPLIER_<N>_BASE_URL for each supplier configured
- STORE_API_KEY (optional) for pushing updates to your live store
"""

import os
import time
import logging
import requests
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional, Tuple

# --- Configure logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("smart_supply_core")

# --- === Placeholder DB functions (replace with your actual DB layer) === ---
def fetch_all_tracked_products() -> List[Dict]:
    """
    Returns a list of product dicts you want to sync/update.
    Each product dict should include at least:
        - id: internal product id
        - sku: product sku or external identifier
        - supplier_entries: list of supplier entry ids for this product
        - current_selling_price: current price in your store (Decimal/float)
        - minimum_margin: minimum profit in USD (or currency) you require per unit
    Replace this with your actual DB query.
    """
    # Example static return for illustration:
    return [
        {
            "id": 1234,
            "sku": "TWS-EBUD-01",
            "name": "Wireless Earbuds Model X",
            "supplier_entries": [1, 2],
            "current_selling_price": Decimal("19.60"),
            "minimum_margin": Decimal("5.00")
        },
        # add more...
    ]

def fetch_supplier_entry(supplier_entry_id: int) -> Dict:
    """
    Fetch supplier entry details from DB by id. Must return:
      - id
      - supplier_name
      - supplier_product_id (id used by supplier API)
      - supplier_id (your supplier record id)
      - quality_score (0-100)
      - last_known_stock
      - last_known_price (supplier unit price)
      - supplier_api_key_env (name of env var that stores API key)
      - supplier_base_url (base API URL)
    Replace this with your DB call.
    """
    # Example stubs (replace)
    if supplier_entry_id == 1:
        return {
            "id": 1,
            "supplier_name": "SupplierAlpha",
            "supplier_product_id": "ALPHA-TWS-01",
            "supplier_id": 11,
            "quality_score": 90,
            "last_known_stock": 500,
            "last_known_price": Decimal("5.00"),
            "supplier_api_key_env": "SUPPLIER_ALPHA_API_KEY",
            "supplier_base_url": "https://api.supplieralpha.com"
        }
    else:
        return {
            "id": 2,
            "supplier_name": "SupplierBeta",
            "supplier_product_id": "BETA-TWS-101",
            "supplier_id": 12,
            "quality_score": 85,
            "last_known_stock": 120,
            "last_known_price": Decimal("4.80"),
            "supplier_api_key_env": "SUPPLIER_BETA_API_KEY",
            "supplier_base_url": "https://api.supplierbeta.com"
        }

def update_supplier_entry_price_and_stock(supplier_entry_id: int, price: Decimal, stock: int):
    """
    Persist supplier price & stock to DB.
    """
    logger.info(f"DB: update supplier entry {supplier_entry_id} -> price={price} stock={stock}")

def update_product_selling_price(product_id: int, new_price: Decimal):
    """
    Persist new selling price for the product in DB.
    """
    logger.info(f"DB: update product {product_id} selling_price -> {new_price}")

def record_price_change(product_id: int, old_price: Decimal, new_price: Decimal, reason: str):
    """
    Save a price change audit record for traceability.
    """
    logger.info(f"DB: record price change {product_id}: {old_price} -> {new_price} ({reason})")


# --- === Supplier API helpers === ---
class SupplierClient:
    def __init__(self, api_key: str, base_url: str, timeout: int = 8):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def get_product_info(self, supplier_product_id: str) -> Dict:
        """
        Query supplier product endpoint for price & stock. Supplier API contract assumed:
            GET /products/{supplier_product_id}
            returns JSON with fields: { "price": "4.50", "stock": 120 }
        Adapt to actual supplier API.
        """
        url = f"{self.base_url}/products/{supplier_product_id}"
        logger.debug(f"Supplier API request GET {url}")
        resp = requests.get(url, headers=self.headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def get_shipping_options(self, supplier_product_id: str, qty: int, destination: Dict) -> List[Dict]:
        """
        Optional: get shipping options. Not used directly here but available for enhancements.
        """
        url = f"{self.base_url}/shipping"
        payload = {"product_id": supplier_product_id, "quantity": qty, "destination": destination}
        resp = requests.post(url, json=payload, headers=self.headers, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json().get("options", [])


# --- === Competitor price fetcher (placeholder) === ---
def fetch_competitor_prices_for_sku(sku: str) -> List[Decimal]:
    """
    Implement a real competitor price fetcher: web-scraper, price-API, or SERP API.
    Here we provide a stub with dummy values — replace with real logic.
    Return a list of competitor prices (Decimal).
    """
    # TODO: Replace with real scraping / API
    dummy = {
        "TWS-EBUD-01": [Decimal("20.00"), Decimal("21.50"), Decimal("19.80")],
    }
    prices = dummy.get(sku, [])
    logger.debug(f"Fetched competitor prices for {sku}: {prices}")
    return prices


# --- === Pricing utilities === ---
def decimal_round(x: Decimal, places: int = 2) -> Decimal:
    quant = Decimal("1." + "0" * places)
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def compute_target_price_from_competitors(competitor_prices: List[Decimal]) -> Optional[Decimal]:
    """
    Average competitor price, then apply 2% lower rule.
    Return None if no competitor prices.
    """
    if not competitor_prices:
        return None
    avg = sum(competitor_prices) / Decimal(len(competitor_prices))
    target = avg * Decimal("0.98")  # 2% lower
    return decimal_round(target)

def ensure_minimum_margin(target_price: Decimal, supplier_unit_cost: Decimal, minimum_margin: Decimal) -> Decimal:
    """
    Ensure target_price gives at least minimum_margin; if not, raise a flag or adjust.
    We will ensure final price >= supplier_unit_cost + minimum_margin. If not possible, return None.
    """
    floor = supplier_unit_cost + minimum_margin
    if target_price < floor:
        # we must raise price to floor to maintain margin
        return decimal_round(floor)
    return target_price


# --- === Core sync logic for a single product === ---
def sync_product_price(product: Dict):
    """
    Sync logic for one product:
    - Fetch supplier entries
    - Query supplier APIs for price & stock
    - Fetch competitor prices
    - Compute new price (2% lower than avg competitor), ensure margin
    - Update DB/store if price changed meaningfully
    """
    product_id = product["id"]
    sku = product["sku"]
    minimum_margin: Decimal = Decimal(product.get("minimum_margin", "0.00"))
    logger.info(f"Syncing product {product_id} (sku={sku})")

    # Gather supplier candidates
    supplier_entries = product.get("supplier_entries", [])
    suppliers_info = []
    for entry_id in supplier_entries:
        entry = fetch_supplier_entry(entry_id)
        # get API key from env
        api_key_env = entry.get("supplier_api_key_env")
        api_key = os.getenv(api_key_env)
        base_url = entry.get("supplier_base_url")
        if not api_key or not base_url:
            logger.warning(f"Missing API key or base_url for supplier entry {entry_id} ({entry.get('supplier_name')})")
            continue

        client = SupplierClient(api_key=api_key, base_url=base_url)
        try:
            info = client.get_product_info(entry["supplier_product_id"])
            supplier_price = Decimal(str(info.get("price")))
            supplier_stock = int(info.get("stock", 0))
            # Persist supplier snapshot to DB
            update_supplier_entry_price_and_stock(entry_id, supplier_price, supplier_stock)
            suppliers_info.append({
                "entry_id": entry_id,
                "supplier_name": entry["supplier_name"],
                "supplier_id": entry["supplier_id"],
                "quality_score": entry.get("quality_score", 0),
                "unit_cost": supplier_price,
                "stock": supplier_stock,
                "client": client
            })
        except Exception as e:
            logger.error(f"Failed to fetch product info from supplier {entry.get('supplier_name')}: {e}")

    if not suppliers_info:
        logger.warning(f"No available suppliers for product {product_id}. Skipping.")
        return

    # Filter for quality threshold (e.g., >= 70)
    quality_threshold = 70
    candidates = [s for s in suppliers_info if s["stock"] > 0 and s["quality_score"] >= quality_threshold]
    if not candidates:
        logger.warning(f"No high-quality in-stock suppliers found for product {product_id}. Considering all in-stock suppliers.")
        candidates = [s for s in suppliers_info if s["stock"] > 0]
        if not candidates:
            logger.warning(f"No in-stock suppliers at all for product {product_id}. Aborting price sync.")
            return

    # Choose the supplier with lowest unit_cost, tiebreaker highest quality then lowest stock latency
    candidates = sorted(candidates, key=lambda s: (s["unit_cost"], -s["quality_score"]))
    chosen = candidates[0]
    chosen_cost = chosen["unit_cost"]
    logger.info(f"Chosen supplier for product {product_id}: {chosen['supplier_name']} (cost={chosen_cost}, stock={chosen['stock']})")

    # Fetch competitor prices
    competitor_prices = fetch_competitor_prices_for_sku(sku)
    target_price = compute_target_price_from_competitors(competitor_prices)

    # Fallback: if no competitor price, set price as chosen_cost + 2x margin or a markup
    if target_price is None:
        logger.info("No competitor prices found; using supplier_cost markup fallback.")
        fallback_markup = Decimal("2.50")  # e.g., multiplier, or supplier_cost + fixed margin
        target_price = decimal_round(chosen_cost * fallback_markup)

    # Ensure minimum margin
    final_price = ensure_minimum_margin(target_price, chosen_cost, minimum_margin)
    if final_price is None:
        logger.warning(f"Unable to meet minimum margin for product {product_id}. Supplier cost {chosen_cost} + min_margin {minimum_margin} exceeds target price {target_price}.")
        # Optionally: mark product as non-competitive, disable listing, or alert human
        record_price_change(product_id, Decimal(product["current_selling_price"]), Decimal(product["current_selling_price"]), "margin_issue")
        return

    # Round and enforce pricing rules (e.g., .99 endings)
    # Example: keep to two decimals
    final_price = decimal_round(final_price)

    # If final_price differs materially, update store and DB
    old_price = Decimal(product["current_selling_price"])
    price_diff = (final_price - old_price).copy_abs()
    price_change_threshold = Decimal("0.05")  # only update if at least 5 cents change
    if price_diff >= price_change_threshold:
        reason = "auto_sync_competitor_pricing"
        logger.info(f"Updating product {product_id} price {old_price} -> {final_price} (reason={reason})")
        update_product_selling_price(product_id, final_price)
        record_price_change(product_id, old_price, final_price, reason)
        # Optionally call external store API to push price change live
        push_price_to_store_api(product_id, final_price)
    else:
        logger.debug(f"No meaningful price change for product {product_id}: old={old_price}, new={final_price}")

# --- === External Store push (optional) === ---
def push_price_to_store_api(product_id: int, new_price: Decimal):
    """
    Optionally push price update to your live store via API.
    Requires STORE_API_KEY in env and store API endpoint implementation.
    """
    store_api_key = os.getenv("STORE_API_KEY")
    store_base = os.getenv("STORE_BASE_URL")  # e.g., https://api.yourstore.com
    if not store_api_key or not store_base:
        logger.debug("STORE API not configured; skipping push to store.")
        return
    url = f"{store_base.rstrip('/')}/products/{product_id}/price"
    headers = {"Authorization": f"Bearer {store_api_key}", "Content-Type": "application/json"}
    payload = {"price": str(new_price)}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=8)
        resp.raise_for_status()
        logger.info(f"Pushed new price for product {product_id} to store API.")
    except Exception as e:
        logger.error(f"Failed to push price to store API for product {product_id}: {e}")


# --- === Main run loop / orchestration === ---
def run_sync_cycle():
    """
    One cycle execution, safe to call from a scheduler.
    """
    products = fetch_all_tracked_products()
    for product in products:
        try:
            sync_product_price(product)
        except Exception as e:
            logger.exception(f"Unhandled exception syncing product {product.get('id')}: {e}")


if __name__ == "__main__":
    # Example: run one cycle. In production, run periodically or via serverless cron.
    logger.info("Starting smart_supply_core run cycle")
    run_sync_cycle()
    logger.info("Run cycle finished")
