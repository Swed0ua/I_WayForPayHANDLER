import os
from dotenv import load_dotenv
from services.WayForPay.wayForPayAdapter import WayForPayAdapter
from services.WayForPay.wayForPayService import WayForPayService
from utils import get_day_timestamp_range

load_dotenv()


def run_payments_statistics_task_for_day(days_ago: int = -1) -> None: 
    start_ts, end_ts = get_day_timestamp_range(days_ago=days_ago)

    merchant_account = os.getenv("WAYFORPAY_MERCHANT_ACCOUNT")
    merchant_secret = os.getenv("WAYFORPAY_MERCHANT_SECRET_KEY")

    if not merchant_account or not merchant_secret:
        raise ValueError("WAYFORPAY_MERCHANT_ACCOUNT and WAYFORPAY_MERCHANT_SECRET_KEY must be set")

    service = WayForPayService(merchant_account=merchant_account, merchant_secret_key=merchant_secret)

    result = service.get_payments(
        date_begin=str(start_ts),
        date_end=str(end_ts),
        merchant_account=merchant_account,
    )

    transaction_list = result.get("transactionList", [])
    suitable_transactions = WayForPayAdapter.extract_suitable_items(transaction_list=transaction_list)

    calculated_amount_dict = WayForPayAdapter.group_transactions_by_amount(transaction_list=suitable_transactions)

    print("calculated_amount_dict", calculated_amount_dict)