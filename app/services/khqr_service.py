import os
import io
import json
import base64
import logging
import urllib.request
from bakong_khqr import KHQR, KHQRConfig

logger = logging.getLogger(__name__)

# In-memory stable QR cache so an order's QR code does not mutate on 3s refresh
ORDER_QR_CACHE = {}


class KHQRService:
    def __init__(self):
        token = os.getenv("BAKONG_TOKEN")
        relay_url = os.getenv("KHQR_RELAY_BASE_URL")

        if relay_url:
            config = KHQRConfig(token=token, base_url=relay_url)
            self.khqr = KHQR(config=config)
        else:
            self.khqr = KHQR(token)

        self.token = token
        self.account_id = os.getenv("BAKONG_ACCOUNT_ID") or "sary_chanpich@aclb"
        self.merchant_name = os.getenv("MERCHANT_NAME", "CHANPECH SARI")
        self.merchant_city = os.getenv("MERCHANT_CITY", "Phnom Penh")
        self.store_label = os.getenv("STORE_LABEL", "ZANDO")
        self.phone_number = os.getenv("MERCHANT_PHONE", "8558670524")
        self.currency = os.getenv("CURRENCY", "USD")

    def generate_order_qr(self, amount: float, bill_number: str) -> dict:
        """
        Generates standard EMVCo KHQR code, computes MD5 hash,
        and renders a base64 data URI image.
        Caches the result so the same bill_number retains the exact same MD5 and QR code.
        """
        if bill_number in ORDER_QR_CACHE:
            return ORDER_QR_CACHE[bill_number]

        try:
            qr_result = self.khqr.create_qr(
                account_id=self.account_id,
                merchant_name=self.merchant_name,
                merchant_city=self.merchant_city,
                amount=round(float(amount), 2),
                currency=self.currency,
                store_label=self.store_label,
                phone_number=self.phone_number,
                bill_number=bill_number,
                terminal_label="WebCheckout",
            )
            qr_string = str(qr_result)
        except Exception as e:
            logger.warning(f"Error calling create_qr: {e}. Falling back to default EMVCo format.")
            qr_string = f"KHQR:{self.account_id}:{amount}:{bill_number}"

        try:
            md5_hash = self.khqr.generate_md5(qr_string)
        except Exception:
            import hashlib
            md5_hash = hashlib.md5(qr_string.encode("utf-8")).hexdigest()

        try:
            qr_image_uri = self.khqr.qr_image(qr=qr_string, format="base64_uri")
        except Exception as e:
            logger.warning(f"Error rendering KHQR image with bakong-khqr: {e}. Using qrcode library fallback.")
            import qrcode
            qr = qrcode.QRCode(box_size=8, border=2)
            qr.add_data(qr_string)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            qr_image_uri = f"data:image/png;base64,{b64}"

        result = {
            "qr_string": qr_string,
            "md5": md5_hash,
            "qr_image": qr_image_uri,
        }
        ORDER_QR_CACHE[bill_number] = result
        return result

    def verify_payment(self, md5_hash: str) -> dict:
        """
        Verifies payment status with NBC Bakong Open API using the MD5 hash.
        """
        if not md5_hash or not self.token or self.token.endswith("..."):
            return {"status": "UNPAID", "details": None}

        try:
            status = self.khqr.check_payment(md5_hash)
            payment_details = self.khqr.get_payment(md5_hash) if status == "PAID" else None
            return {"status": status, "details": payment_details}
        except Exception as e:
            logger.info(f"Bakong payment check: {e}")
            return {"status": "UNPAID", "details": None}

    def verify_by_short_hash(self, short_hash: str, amount: float, currency: str = "USD") -> dict:
        """
        Verifies transaction status using Bakong 8-character Short Hash (e.g. from receipt).
        Calls /v1/check_transaction_by_short_hash.
        """
        if not short_hash or not self.token or self.token.endswith("..."):
            return {"status": "UNPAID", "details": None}

        clean_hash = short_hash.strip().lower()
        if len(clean_hash) > 8:
            clean_hash = clean_hash[:8]

        try:
            url = "https://api-bakong.nbc.gov.kh/v1/check_transaction_by_short_hash"
            payload = {
                "hash": clean_hash,
                "amount": float(amount),
                "currency": currency.upper() if currency else "USD"
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                    "User-Agent": "Zando-KHQR/1.0",
                }
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("responseCode") == 0 and data.get("data"):
                    return {"status": "PAID", "details": data["data"]}
        except Exception as e:
            logger.info(f"Bakong short hash check error: {e}")

        return {"status": "UNPAID", "details": None}

    def verify_by_hash(self, full_hash: str) -> dict:
        """
        Verifies transaction status using Bakong full 64-char transaction hash.
        Calls /v1/check_transaction_by_hash.
        """
        if not full_hash or not self.token or self.token.endswith("..."):
            return {"status": "UNPAID", "details": None}

        try:
            url = "https://api-bakong.nbc.gov.kh/v1/check_transaction_by_hash"
            payload = {"hash": full_hash.strip()}
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                    "User-Agent": "Zando-KHQR/1.0",
                }
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("responseCode") == 0 and data.get("data"):
                    return {"status": "PAID", "details": data["data"]}
        except Exception as e:
            logger.info(f"Bakong full hash check error: {e}")

        return {"status": "UNPAID", "details": None}
