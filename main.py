from nocodb import NocoDB
from store_manager import StoreManager
from marketing_ai import MarketingAI
from invoice_payment import InvoicePayment
from chat_ai import ChatAI
from config import NOCODB_API_URL, NOCODB_TOKEN
import time

def main():
    print("🧠 ThunderBrain Online... Initializing systems...")

    # Initialize systems
    nocodb = NocoDB(api_url=NOCODB_API_URL, token=NOCODB_TOKEN)
    store = StoreManager(nocodb)
    marketing = MarketingAI(nocodb)
    payments = InvoicePayment(nocodb)
    chat = ChatAI()

    while True:
        print("⚙️ Running main AI loop...")
        store.sync_inventory()
        store.process_orders()
        payments.generate_invoices()
        marketing.auto_post()
        marketing.analyze_engagement()
        chat.listen_and_reply()

        print("✅ Cycle complete. Sleeping for 5 minutes...")
        time.sleep(300)

if __name__ == "__main__":
    main()
