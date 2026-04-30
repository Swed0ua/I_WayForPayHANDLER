import os
from services.B24.B24Config import DEFAULT_DEAL_FIELD_MAPPING, DEFAULT_TARIFFS_DATA


class B24Adapter:
    default_deal_field_mapping = DEFAULT_DEAL_FIELD_MAPPING
    default_tariffs_data = DEFAULT_TARIFFS_DATA
    base_tariff_product_ids = [324, 2, 336]

    @staticmethod
    def to_deal_fields(
        data: dict,
        field_mapping: dict[str, str] | None = None,
    ) -> dict[str, any]:
        mapping = field_mapping or B24Adapter.default_deal_field_mapping
        return {
            b24_field: data.get(our_key)
            for our_key, b24_field in mapping.items()
            if data.get(our_key) is not None
        }

    @staticmethod
    def get_tariff_title(amount: str) -> dict:
        return B24Adapter.default_tariffs_data.get(amount, B24Adapter.default_tariffs_data["default"])["title"]
    
    @staticmethod
    def to_product_rows(calculated_amount_dict: dict, amount_to_product_id: dict) -> tuple[list[dict], list[dict]]:
        product_rows = []
        unmatched = []
        mapping = amount_to_product_id

        for amount_key, data in calculated_amount_dict.items():
            amount_str = str(amount_key).strip()
            try:
                amount_normalized = str(int(float(amount_str)))
            except (TypeError, ValueError):
                amount_normalized = amount_str
            product_id = mapping.get(amount_str) or mapping.get(amount_normalized)

            count = data.get("count", 0)
            if count <= 0:
                continue

            if product_id is None:
                unmatched.append({"amount": amount_str, "count": count})
                continue

            try:
                price = float(data.get("amount_value", amount_str))
            except (TypeError, ValueError):
                price = 0.0

            product_rows.append({
                "PRODUCT_ID": product_id,
                "QUANTITY": float(count),
                "PRICE": price,
            })

        return product_rows, unmatched

    @staticmethod
    def to_base_tariff_rows(calculated_amount_dict: dict, products: list[dict]) -> tuple[list[dict], dict]:
        base_tariffs = []
        for p in products:
            try:
                pid = int(p.get("ID"))
            except (TypeError, ValueError):
                continue
            if pid not in B24Adapter.base_tariff_product_ids:
                continue
            try:
                amount = float(p.get("PRICE"))
            except (TypeError, ValueError):
                continue
            base_tariffs.append({"product_id": pid, "amount": amount})

        base_tariffs.sort(key=lambda t: B24Adapter.base_tariff_product_ids.index(t["product_id"]))
        quantity_by_product_id: dict[int, float] = {}
        unmatched: dict = {}

        for amount_key, data in calculated_amount_dict.items():
            amount_str = str(amount_key).strip()
            count = data.get("count", 0)
            if count <= 0:
                continue

            try:
                amount_value = float(data.get("amount_value", amount_str))
            except (TypeError, ValueError):
                unmatched[amount_key] = data
                continue

            matched = False
            for tariff in base_tariffs:
                quotient, remainder = divmod(amount_value, tariff["amount"])
                if abs(remainder) < 1e-9:
                    pid = tariff["product_id"]
                    quantity_by_product_id[pid] = quantity_by_product_id.get(pid, 0.0) + float(quotient * count)
                    matched = True
                    break

            if not matched:
                unmatched[amount_key] = data

        product_rows = []
        for tariff in base_tariffs:
            pid = tariff["product_id"]
            quantity = quantity_by_product_id.get(pid, 0.0)
            if quantity <= 0:
                continue
            product_rows.append({
                "PRODUCT_ID": pid,
                "QUANTITY": float(quantity),
                "PRICE": float(tariff["amount"]),
            })

        return product_rows, unmatched

    @staticmethod
    def format_unmatched_comment(unmatched: list[dict]) -> str:
        if not unmatched:
            return ""
        parts = [f"({item['amount']} x {item['count']}шт.)" for item in unmatched]
        return "Не знайдені товарні картки: " + " ".join(parts)

    @staticmethod
    def format_default_fields() -> dict:
        return {
            "UF_CRM_1682949203": os.getenv("WAY_FOR_PAY_EDRPOU"),
            "CONTACT_ID": os.getenv("WAY_FOR_PAY_CONTACT_ID"),
        }