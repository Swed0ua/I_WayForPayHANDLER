import os
import sqlite3
from datetime import datetime
from typing import Optional

_DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "transactions.db")


def _get_connection(db_path: Optional[str] = None):
    path = db_path or os.getenv("DB_PATH") or _DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    return sqlite3.connect(path)


def init_schema(db_path: Optional[str] = None) -> None:
    conn = _get_connection(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                orderReference TEXT PRIMARY KEY,
                transactionType TEXT,
                createdDate TEXT,
                amount TEXT,
                currency TEXT,
                transactionStatus TEXT,
                processingDate TEXT,
                reasonCode TEXT,
                reason TEXT,
                email TEXT,
                phone TEXT,
                paymentSystem TEXT,
                cardPan TEXT,
                cardType TEXT,
                issuerBankCountry TEXT,
                issuerBankName TEXT,
                fee TEXT,
                settlementDate TEXT,
                CREATE_BD_DATE TEXT NOT NULL,
                UPDATE_BD_DATE TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


# Поля з API WayForPay (transactionList item)
_TRANSACTION_COLUMNS = [
    "orderReference", "transactionType", "createdDate", "amount", "currency",
    "transactionStatus", "processingDate", "reasonCode", "reason", "email", "phone",
    "paymentSystem", "cardPan", "cardType", "issuerBankCountry", "issuerBankName",
    "fee", "settlementDate",
]


def upsert_transactions(transaction_list: list[dict], db_path: Optional[str] = None) -> None:
    """Вставляє або оновлює транзакції по orderReference. CREATE_BD_DATE при першому записі, UPDATE_BD_DATE при оновленні."""
    if not transaction_list:
        return
    init_schema(db_path)
    conn = _get_connection(db_path)
    now = datetime.utcnow().isoformat() + "Z"
    try:
        for t in transaction_list:
            order_ref = t.get("orderReference") or ""
            if not order_ref:
                continue
            values = [str(t.get(k, "") or "") for k in _TRANSACTION_COLUMNS]
            cur = conn.execute(
                "SELECT 1 FROM transactions WHERE orderReference = ?",
                (order_ref,),
            )
            if cur.fetchone() is None:
                conn.execute(
                    """INSERT INTO transactions (
                        orderReference, transactionType, createdDate, amount, currency,
                        transactionStatus, processingDate, reasonCode, reason, email, phone,
                        paymentSystem, cardPan, cardType, issuerBankCountry, issuerBankName,
                        fee, settlementDate, CREATE_BD_DATE, UPDATE_BD_DATE
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    values + [now, now],
                )
            else:
                conn.execute(
                    """UPDATE transactions SET
                        transactionType=?, createdDate=?, amount=?, currency=?,
                        transactionStatus=?, processingDate=?, reasonCode=?, reason=?, email=?, phone=?,
                        paymentSystem=?, cardPan=?, cardType=?, issuerBankCountry=?, issuerBankName=?,
                        fee=?, settlementDate=?, UPDATE_BD_DATE=?
                    WHERE orderReference=?""",
                    values[1:] + [now, order_ref],
                )
        conn.commit()
    finally:
        conn.close()


def get_transactions_by_settlement_date(
    start_ts: int, end_ts: int, db_path: Optional[str] = None
) -> list[dict]:
    """Повертає транзакції з БД, у яких settlementDate в діапазоні [start_ts, end_ts]. Формат як у API."""
    conn = _get_connection(db_path)
    try:
        cur = conn.execute(
            """SELECT orderReference, transactionType, createdDate, amount, currency,
                      transactionStatus, processingDate, reasonCode, reason, email, phone,
                      paymentSystem, cardPan, cardType, issuerBankCountry, issuerBankName,
                      fee, settlementDate FROM transactions
               WHERE CAST(settlementDate AS INTEGER) >= ? AND CAST(settlementDate AS INTEGER) <= ?""",
            (start_ts, end_ts),
        )
        rows = cur.fetchall()
        keys = [c[0] for c in cur.description]
        return [dict(zip(keys, row)) for row in rows]
    finally:
        conn.close()
