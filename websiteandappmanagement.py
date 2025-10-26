import requests
import json
from datetime import datetime

class WebsiteAppManager:
    def __init__(self, nocodb_url, api_token):
        self.nocodb_url = nocodb_url.rstrip('/')
        self.headers = {
            "accept": "application/json",
            "xc-token": api_token,
            "Content-Type": "application/json"
        }

    # --------------------------
    # WEBSITE MANAGEMENT LOGIC
    # --------------------------
    def get_website_data(self):
        """Fetch current website products, pages, and user activity."""
        url = f"{self.nocodb_url}/api/v1/website_data"
        res = requests.get(url, headers=self.headers)
        if res.status_code == 200:
            return res.json()
        return {"error": res.text}

    def update_website_content(self, content_id, updates):
        """Update website sections — e.g., banners, products, or blog posts."""
        url = f"{self.nocodb_url}/api/v1/website_data/{content_id}"
        res = requests.patch(url, headers=self.headers, data=json.dumps(updates))
        return res.json()

    def post_new_product(self, product):
        """Automatically post new product listings on the store website."""
        url = f"{self.nocodb_url}/api/v1/products"
        res = requests.post(url, headers=self.headers, data=json.dumps(product))
        return res.json()

    # --------------------------
    # APP MANAGEMENT LOGIC
    # --------------------------
    def sync_app_with_website(self):
        """Sync app products, offers, and updates with the website."""
        website_data = self.get_website_data()
        if "error" in website_data:
            return website_data
        app_payload = {
            "lastSynced": datetime.utcnow().isoformat(),
            "websiteProducts": len(website_data.get("list", []))
        }
        url = f"{self.nocodb_url}/api/v1/app_sync"
        res = requests.post(url, headers=self.headers, data=json.dumps(app_payload))
        return res.json()

    def push_notification(self, message, target="users"):
        """Send push notifications or updates to app users."""
        url = f"{self.nocodb_url}/api/v1/notifications"
        payload = {
            "message": message,
            "target": target,
            "timestamp": datetime.utcnow().isoformat()
        }
        res = requests.post(url, headers=self.headers, data=json.dumps(payload))
        return res.json()

    # --------------------------
    # AUTOMATION & ANALYTICS
    # --------------------------
    def analyze_performance(self):
        """Pull analytics data and generate sales & engagement insights."""
        url = f"{self.nocodb_url}/api/v1/analytics"
        res = requests.get(url, headers=self.headers)
        if res.status_code == 200:
            data = res.json()
            report = {
                "total_sales": sum(item.get("sales", 0) for item in data.get("list", [])),
                "top_product": max(data.get("list", []), key=lambda x: x.get("sales", 0), default={}),
                "average_engagement": round(sum(item.get("engagement", 0) for item in data.get("list", [])) / max(len(data.get("list", [])), 1), 2)
            }
            return report
        return {"error": res.text}

    def auto_market_products(self):
        """Auto-post promotional content and manage social media integration."""
        marketing_message = "🔥 New deals available! Visit our app & website now!"
        return self.push_notification(marketing_message, target="followers")

# --------------------------
# EXAMPLE USAGE
# --------------------------
if __name__ == "__main__":
    nocodb_url = "https://api.nocodb.com"  # replace with your NocoDB URL
    token = "YOUR_NOCODB_TOKEN"

    manager = WebsiteAppManager(nocodb_url, token)
    print(manager.analyze_performance())
    print(manager.auto_market_products())
