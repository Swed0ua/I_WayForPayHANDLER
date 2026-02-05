class WayForPayAdapter:
    @staticmethod
    def extract_suitable_items(transaction_list: dict) -> list[dict]:
        return [transaction for transaction in transaction_list if transaction.get("transactionStatus") == "ACCEPTED"]

    @staticmethod
    def group_transactions_by_amount(transaction_list: dict) -> dict:
        calculated_amount_dict = {}

        for transaction in transaction_list:
            transaction_amount = transaction.get("amount")
            if transaction_amount not in calculated_amount_dict:
                calculated_amount_dict[transaction_amount] = {"count": 0, "amount_value": transaction_amount, "items": []}
            
            calculated_amount_dict[transaction_amount]["count"] += 1
            calculated_amount_dict[transaction_amount]["items"].append(transaction)

        return calculated_amount_dict