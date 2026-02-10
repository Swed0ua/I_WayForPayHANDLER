class B24Adapter:
    DEFAULT_DEAL_FIELD_MAPPING = {
        "title": "TITLE",
        "stage_id": "STAGE_ID",
        "category_id": "CATEGORY_ID",
        "amount": "OPPORTUNITY",
    }

    DEFAULT_TARIFFS_DATA = {
        "default": {
            "title": "Надання послуги",
        }
    }

    @staticmethod
    def to_deal_fields(
        data: dict,
        field_mapping: dict[str, str] | None = None,
    ) -> dict[str, any]:
        mapping = field_mapping or B24Adapter.DEFAULT_DEAL_FIELD_MAPPING
        return {
            b24_field: data.get(our_key)
            for our_key, b24_field in mapping.items()
            if data.get(our_key) is not None
        }

    @staticmethod
    def get_tariff_title(amount: str) -> dict:
        return B24Adapter.DEFAULT_TARIFFS_DATA.get(amount, B24Adapter.DEFAULT_TARIFFS_DATA["default"])["title"]