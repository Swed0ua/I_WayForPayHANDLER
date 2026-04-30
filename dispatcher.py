import base64
import csv
import os
import zipfile
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config import BITRIX24_DEAL_AMMOUNT_STATISTICS_COLUMN_ID, BITRIX24_DEAL_CATEGORY_ID
from services.B24.B24Adapter import B24Adapter
from services.B24.B24Config import CATALOG_PRODUCT_ID
from services.B24.B24Servece import B24Service
from services.Db.db import get_transactions_by_settlement_date, upsert_transactions
from services.ExcelExport.ExcelExportService import ExcelExportService
from services.WayForPay.wayForPayAdapter import WayForPayAdapter
from services.WayForPay.wayForPayService import WayForPayService
from utils import format_timestamp_to_date, get_day_timestamp_range

load_dotenv()

_GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
_PROJECT_ROOT = Path(__file__).resolve().parent
_GMAIL_CLIENT_SECRET = _PROJECT_ROOT / "client_secret_20102510405-9bbtqpruq63hgiedpqu25cqv9tqrgck1.apps.googleusercontent.com.json"
_GMAIL_TOKEN = _PROJECT_ROOT / "token.json"
_WAYFORPAY_FROM = "notify@wayforpay.com.ua"


def _gmail_service():
    creds = None
    if _GMAIL_TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(_GMAIL_TOKEN), _GMAIL_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(_GMAIL_CLIENT_SECRET), _GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        _GMAIL_TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return build("gmail", "v1", credentials=creds)


def _gmail_plain_body(payload: dict) -> str:
    data = (payload.get("body") or {}).get("data")
    if data:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    for part in payload.get("parts") or []:
        if part.get("mimeType") == "text/plain":
            d = (part.get("body") or {}).get("data")
            if d:
                return base64.urlsafe_b64decode(d).decode("utf-8", errors="replace")
        inner = _gmail_plain_body(part)
        if inner:
            return inner
    return ""


def _attachment_count(payload: dict) -> int:
    n = 1 if (payload.get("filename") or "").strip() else 0
    for sub in payload.get("parts") or []:
        n += _attachment_count(sub)
    return n


def _attachment_filenames(payload: dict) -> list[str]:
    names: list[str] = []
    fn = (payload.get("filename") or "").strip()
    if fn:
        names.append(fn)
    for sub in payload.get("parts") or []:
        names.extend(_attachment_filenames(sub))
    return names


def _iter_parts(part: dict):
    yield part
    for sub in part.get("parts") or []:
        yield from _iter_parts(sub)


def _part_raw_bytes(svc, message_id: str, part: dict):
    body = part.get("body") or {}
    aid = body.get("attachmentId")
    if aid:
        att = svc.users().messages().attachments().get(userId="me", messageId=message_id, id=aid).execute()
        return base64.urlsafe_b64decode(att["data"])
    data = body.get("data")
    if data:
        return base64.urlsafe_b64decode(data)
    return None


def _print_first_csv_from_zip(zip_bytes: bytes) -> None:
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csv_names:
            return
        with zf.open(csv_names[0]) as f:
            print(f.read().decode("utf-8-sig", errors="replace"))


def _first_csv_from_zip(zip_bytes: bytes) -> bytes | None:
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csv_names:
            return None
        with zf.open(csv_names[0]) as f:
            return f.read()


def _first_zip_csv_bytes_for_day(days_ago: int = 0) -> bytes | None:
    day = date.today() + timedelta(days=days_ago)
    nxt = day + timedelta(days=1)
    q = f"from:{_WAYFORPAY_FROM} after:{day:%Y/%m/%d} before:{nxt:%Y/%m/%d}"
    svc = _gmail_service()
    listed = svc.users().messages().list(userId="me", q=q).execute()
    for item in listed.get("messages", []):
        msg = svc.users().messages().get(userId="me", id=item["id"], format="full").execute()
        payload = msg.get("payload") or {}
        for part in _iter_parts(payload):
            fn = (part.get("filename") or "").lower()
            if not fn.endswith(".zip"):
                continue
            raw = _part_raw_bytes(svc, item["id"], part)
            if not raw:
                continue
            try:
                csv_bytes = _first_csv_from_zip(raw)
                if csv_bytes:
                    return csv_bytes
            except zipfile.BadZipFile:
                continue
    return None


def _csv_rows_grouped_by_day(csv_bytes: bytes) -> dict[str, list[dict]]:
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.reader(text.splitlines(), delimiter=";", quotechar='"')
    rows = list(reader)
    if len(rows) <= 1:
        return {}

    grouped: dict[str, list[dict]] = {}
    for row in rows[1:]:
        if len(row) < 7:
            continue
        request_dt = (row[2] or "").strip()
        amount_raw = (row[4] or "").strip().replace(",", ".")
        status = (row[6] or "").strip()
        if not request_dt or not amount_raw:
            continue
        if status != "Approved":
            continue
        try:
            day = datetime.strptime(request_dt, "%d.%m.%Y %H:%M:%S").strftime("%d.%m.%Y")
            amount = float(amount_raw)
        except ValueError:
            continue

        grouped.setdefault(day, []).append({
            "amount": amount,
            "transactionStatus": status,
        })
    return grouped


def run_payments_statistics_task_from_gmail_csv(days_ago: int = 0) -> None:
    try:
        csv_bytes = _first_zip_csv_bytes_for_day(days_ago=days_ago)
        if not csv_bytes:
            print("[WayForPay/Gmail] CSV not found in ZIP attachments.")
            return

        grouped_by_day = _csv_rows_grouped_by_day(csv_bytes=csv_bytes)
        if not grouped_by_day:
            print("[WayForPay/Gmail] No suitable Approved rows in CSV.")
            return

        b24_webhook_url = os.getenv("BITRIX24_WEBHOOK_URL")
        b24_service = B24Service(webhook_url=b24_webhook_url)
        products = b24_service.get_products(catalog_id=CATALOG_PRODUCT_ID)
        amount_to_product_id = b24_service.build_amount_to_product_id(products=products)

        for chosen_date, transaction_list in sorted(grouped_by_day.items()):
            calculated_amount_dict = WayForPayAdapter.group_transactions_by_amount(transaction_list=transaction_list)
            print(f"[WayForPay/Gmail] {chosen_date} transactions:", len(transaction_list))

            base_product_rows, remaining_calculated_amount_dict = B24Adapter.to_base_tariff_rows(
                calculated_amount_dict=calculated_amount_dict,
                products=products,
            )
            product_rows, unmatched = B24Adapter.to_product_rows(
                calculated_amount_dict=remaining_calculated_amount_dict,
                amount_to_product_id=amount_to_product_id,
            )
            product_rows = base_product_rows + product_rows

            total_amount = sum(
                float(data.get("amount_value", 0) or 0) * data.get("count", 0)
                for data in calculated_amount_dict.values()
            )

            fields = B24Adapter.to_deal_fields(data={
                "title": f"{chosen_date} | Статистика платежів | Точна Сума {total_amount}",
                "stage_id": BITRIX24_DEAL_AMMOUNT_STATISTICS_COLUMN_ID,
                "category_id": BITRIX24_DEAL_CATEGORY_ID,
                "amount": total_amount,
            })

            if unmatched:
                fields["COMMENTS"] = B24Adapter.format_unmatched_comment(unmatched=unmatched)

            fields.update(B24Adapter.format_default_fields())

            if product_rows:
                result = b24_service.create_deal_with_products(
                    fields=fields,
                    product_rows=product_rows,
                    currency_id="EUR",
                )
            else:
                result = b24_service.create_deal(fields=fields)

            print(f"[B24/Gmail] {chosen_date} result:", result)
    except Exception as e:
        print("ERROR run_payments_statistics_task_from_gmail_csv:", e)


def print_wayforpay_email_bodies_today() -> None:
    today = date.today() - timedelta(days=1)
    nxt = today + timedelta(days=1)
    q = f"from:{_WAYFORPAY_FROM} after:{today:%Y/%m/%d} before:{nxt:%Y/%m/%d}"
    svc = _gmail_service()
    listed = svc.users().messages().list(userId="me", q=q).execute()
    msgs = listed.get("messages", [])
    if not msgs:
        print(0)
        return
    for item in msgs:
        msg = svc.users().messages().get(userId="me", id=item["id"], format="full").execute()
        pl = msg.get("payload") or {}
        print(_attachment_count(pl))
        for name in _attachment_filenames(pl):
            print(name)
        for part in _iter_parts(pl):
            fn = (part.get("filename") or "").lower()
            if not fn.endswith(".zip"):
                continue
            raw = _part_raw_bytes(svc, item["id"], part)
            if raw:
                _print_first_csv_from_zip(raw)
            break


def run_daily_task(days_ago: int = -1) -> None:
    """О 23:59: дістає транзакції WayForPay за день і записує/оновлює в БД (по orderReference)."""
    try:
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
        upsert_transactions(transaction_list)
        print(f"[WayForPay] Synced {len(transaction_list)} transactions to DB.")
    except Exception as e:
        print("ERROR run_daily_task:", e)


def run_payments_statistics_task_for_day(days_ago: int = -1, isLocalData: bool = True) -> None:
    try:
        start_ts, end_ts = get_day_timestamp_range(days_ago=days_ago)
        chosen_date = format_timestamp_to_date(ts=start_ts)

        if isLocalData:
            transaction_list = get_transactions_by_settlement_date(start_ts, end_ts)
        else:
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
        print("[WayForPay] Suitable transactions:", len(suitable_transactions))

        b24_webhook_url = os.getenv("BITRIX24_WEBHOOK_URL")
        b24_service = B24Service(webhook_url=b24_webhook_url)

        calculated_amount_dict = WayForPayAdapter.group_transactions_by_amount(transaction_list=suitable_transactions)

        excel_export_path = ExcelExportService.write_amount_statistics(amount_dict=calculated_amount_dict)
        print("excel_export_path", excel_export_path)

        products = b24_service.get_products(catalog_id=CATALOG_PRODUCT_ID)
        amount_to_product_id = b24_service.build_amount_to_product_id(products=products)
        base_product_rows, remaining_calculated_amount_dict = B24Adapter.to_base_tariff_rows(
            calculated_amount_dict=calculated_amount_dict,
            products=products,
        )
        product_rows, unmatched = B24Adapter.to_product_rows(
            calculated_amount_dict=remaining_calculated_amount_dict,
            amount_to_product_id=amount_to_product_id,
        )
        product_rows = base_product_rows + product_rows
        print("-- [B24] product_rows", product_rows)
        print("-- [B24] unmatched", unmatched)
        
        total_amount = sum(
            float(data.get("amount_value", 0) or 0) * data.get("count", 0)
            for data in calculated_amount_dict.values()
        )
        print("[B24] total_amount", total_amount)

        fields = B24Adapter.to_deal_fields(data={
            "title": f"{chosen_date} | Статистика платежів | Точна Сума {total_amount}",
            "stage_id": BITRIX24_DEAL_AMMOUNT_STATISTICS_COLUMN_ID,
            "category_id": BITRIX24_DEAL_CATEGORY_ID,
            "amount": total_amount,
        })

        if unmatched:
            unmatched_comment = B24Adapter.format_unmatched_comment(unmatched=unmatched)
            fields["COMMENTS"] = unmatched_comment

        # DEFAULT FIELDS
        fields.update(B24Adapter.format_default_fields())

        if product_rows:
            result = b24_service.create_deal_with_products(
                fields=fields,
                product_rows=product_rows,
                currency_id="EUR",
            )
        else:
            result = b24_service.create_deal(fields=fields)

        print("b24_service result", result)
    except Exception as e:
        print("ERROR:", e)