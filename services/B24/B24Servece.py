import requests

from logging_setup import get_logger

logger = get_logger(__name__)


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

    def get_products(self, catalog_id: str | int) -> list[dict]:
        resp = self._call("crm.product.list", {
            "filter": {"CATALOG_ID": catalog_id},
            "select": ["ID", "NAME", "PRICE", "CURRENCY_ID"]
        })
        products = resp.get("result", [])
        logger.info("B24 products loaded: catalog_id=%s count=%s", catalog_id, len(products))
        return products

    def build_amount_to_product_id(self, products: list[dict]) -> dict[str, int]:
        mapping = {}
        for p in products:
            price = p.get("PRICE")
            if price is None:
                continue

            key = str(int(float(str(price))))
            mapping[key] = int(p["ID"])
            mapping[f"{key}.00"] = int(p["ID"])
        return mapping

    def create_deal(self, fields: dict) -> dict:
        result = self._call("crm.deal.add", {"fields": fields})
        logger.info("B24 deal created: id=%s", result.get("result"))
        return result

    def create_deal_with_products(self, fields, product_rows, currency_id="EUR"):
        if not product_rows:
            return self.create_deal(fields)

        deal_result = self._call("crm.deal.add", {"fields": fields})
        deal_id = deal_result.get("result")
        logger.info("B24 deal created: id=%s", deal_id)

        product_rows_result = self._call("crm.deal.productrows.set", {
            "id": deal_id,
            "rows": product_rows,
            "currencyId": currency_id,
        })
        logger.info("B24 product rows set: deal_id=%s ok=%s rows=%s",
                    deal_id, product_rows_result.get("result"), len(product_rows))

        return deal_result
