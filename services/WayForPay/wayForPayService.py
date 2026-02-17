import hmac
import hashlib
import requests
import json

from services.WayForPay.wayForPayConfig import GET_PAYMENTS_SIGNATURE_KEYS

class WayForPayService:
    def __init__(self, merchant_account:str, merchant_secret_key:str, base_url:str = "https://api.wayforpay.com/api"):
        self.merchant_account = merchant_account
        self.merchant_secret_key = merchant_secret_key
        self.base_url = base_url

    def _build_signature(self, data: dict[str, any], keys_order: list[str]) -> str:
        """
        Builds a signature for the given data and keys order.
        dist data - dictionary with data to sign when keys are in keys_order.
        dist keys_order - list of keys in the order they should be signed.
        return - signature as a hex string.
        """
        sign_str = ";".join(str(data.get(k, "")) for k in keys_order)

        return hmac.new(
            self.merchant_secret_key.encode('utf-8'), 
            sign_str.encode('utf-8'), 
            hashlib.md5).hexdigest()

    def _make_req(self, endpoint: str, method: str = "POST", payload: dict = {}, **kwargs):
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {
            "Content-Type": "application/json",
        }

        if method == "POST":
            response = requests.post(url, json=payload or {}, headers=headers, **kwargs)
        elif method == "GET":
            response = requests.get(url, params=payload, headers=headers, **kwargs)
        else:
            raise ValueError(f"Invalid method: {method}")
        
        response.raise_for_status()
        return response.json()

    def get_payments(self, date_begin: str, date_end: str, merchant_account:str=None, transaction_type="TRANSACTION_LIST"):
        sign_key = self._build_signature(
            data={"merchantAccount": merchant_account or self.merchant_account, "dateBegin": date_begin, "dateEnd": date_end}, 
            keys_order=GET_PAYMENTS_SIGNATURE_KEYS
            )

        print("dateBegin", date_begin)
        print("dateEnd", date_end)

        payload = {
                "apiVersion": 1,
                "transactionType": transaction_type,
                "merchantAccount": merchant_account,
                "merchantSignature": sign_key,
                "dateBegin": int(date_begin),
                "dateEnd": int(date_end)
            }

        return self._make_req(endpoint="payments", method="POST", payload=payload)