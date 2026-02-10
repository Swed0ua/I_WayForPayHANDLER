import requests


class B24Service:
    """
    Service for working with Bitrix24 REST API.
    """

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self._rest_prefix = f"{self.webhook_url}"

    def _call(self, method: str, params: dict | None = None) -> dict:
        """Виклик REST-методу B24."""
        url = f"{self._rest_prefix}/{method}.json"
        payload = params or {}
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()
    
    def create_deal(self, fields: dict) -> dict:
        return self._call("crm.deal.add", {"fields": fields})