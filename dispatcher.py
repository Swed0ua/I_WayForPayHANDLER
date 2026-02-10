import os
from dotenv import load_dotenv
from config import BITRIX24_DEAL_AMMOUNT_STATISTICS_COLUMN_ID, BITRIX24_DEAL_CATEGORY_ID
from services.B24.B24Adapter import B24Adapter
from services.B24.B24Servece import B24Service
from services.ExcelExport.ExcelExportService import ExcelExportService
from services.WayForPay.wayForPayAdapter import WayForPayAdapter
from services.WayForPay.wayForPayService import WayForPayService
from utils import format_timestamp_to_date, get_day_timestamp_range

load_dotenv()


def run_payments_statistics_task_for_day(days_ago: int = -1) -> None: 
    start_ts, end_ts = get_day_timestamp_range(days_ago=days_ago)
    chosen_date = format_timestamp_to_date(ts=start_ts)

    merchant_account = os.getenv("WAYFORPAY_MERCHANT_ACCOUNT")
    merchant_secret = os.getenv("WAYFORPAY_MERCHANT_SECRET_KEY")

    b24_webhook_url = os.getenv("BITRIX24_WEBHOOK_URL")

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

    excel_export_path = ExcelExportService.write_amount_statistics(amount_dict=calculated_amount_dict)
    print("excel_export_path", excel_export_path)

    b24_service = B24Service(webhook_url=b24_webhook_url)
    for amount, data in calculated_amount_dict.items():
        count = data.get("count")
        tariff_title = B24Adapter.get_tariff_title(amount=amount)
        fields =B24Adapter.to_deal_fields(data={
            "title": f"{chosen_date} | {tariff_title} | Сума {amount} x Кількість {count}",
            "stage_id": BITRIX24_DEAL_AMMOUNT_STATISTICS_COLUMN_ID,
            "category_id": BITRIX24_DEAL_CATEGORY_ID,
            "amount": amount,
        })
        result = b24_service.create_deal(fields=fields)
        print("b24_service.create_deal result", result)
        return result