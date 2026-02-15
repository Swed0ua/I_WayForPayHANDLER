from services.B24.B24Config import DEFAULT_DEAL_FIELD_MAPPING, DEFAULT_TARIFFS_DATA


class B24Adapter:
    default_deal_field_mapping = DEFAULT_DEAL_FIELD_MAPPING
    default_tariffs_data = DEFAULT_TARIFFS_DATA

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
    def to_product_rows(calculated_amount_dict: dict, amount_to_product_id: dict[str, int]) -> list[dict]:
        product_rows = []
        mapping = amount_to_product_id
        for amount_key, data in calculated_amount_dict.items():
            amount_str = str(amount_key).strip()
            product_id = mapping.get(amount_str)
            print("amount_str", amount_str)
            print("product_id", product_id)
            if product_id is None:
                continue
            count = data.get("count", 0)
            if count <= 0:
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
        return product_rows