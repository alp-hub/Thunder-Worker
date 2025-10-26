import requests

class NocoDB:
    def __init__(self, api_url, token):
        self.api_url = api_url.rstrip("/")
        self.headers = {"xc-token": token}

    def get_table(self, project, table):
        url = f"{self.api_url}/api/v2/tables/{project}/{table}/records"
        res = requests.get(url, headers=self.headers)
        return res.json() if res.ok else {}

    def insert_record(self, project, table, data):
        url = f"{self.api_url}/api/v2/tables/{project}/{table}/records"
        res = requests.post(url, headers=self.headers, json=data)
        return res.json()

    def update_record(self, project, table, record_id, data):
        url = f"{self.api_url}/api/v2/tables/{project}/{table}/records/{record_id}"
        res = requests.patch(url, headers=self.headers, json=data)
        return res.json()
