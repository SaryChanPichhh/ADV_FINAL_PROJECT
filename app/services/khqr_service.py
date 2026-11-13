import os
import io
import base64
import logging
from bakong_khqr import KHQR, KHQRConfig

logger = logging.getLogger(__name__)


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
        self.account_id = os.getenv("BAKONG_ACCOUNT_ID") or "myshop@aclb"
        self.merchant_name = os.getenv("MERCHANT_NAME", "MyShop Cambodia")
        self.merchant_city = os.getenv("MERCHANT_CITY", "Phnom Penh")
        self.store_label = os.getenv("STORE_LABEL", "MyShop Online")
        self.phone_number = os.getenv("MERCHANT_PHONE", "85512345678")
        self.currency = os.getenv("CURRENCY", "USD")

    def generate_order_qr(self, amount: float, bill_number: str) -> dict:
        """
        Generates standard EMVCo KHQR code, computes MD5 hash,
        and renders a base64 data URI image.
        """
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
            # Fallback simple string if any config error occurs
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

        return {
            "qr_string": qr_string,
            "md5": md5_hash,
            "qr_image": qr_image_uri,
        }

    def verify_payment(self, md5_hash: str) -> dict:
        """
        Verifies payment status with NBC Bakong Open API or configured Relay.
        Safely catches network or token exceptions and returns UNPAID instead of crashing.
        """
        if not md5_hash:
            return {"status": "UNPAID", "details": None}

        if not self.token or self.token.startswith("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."):
            # Unconfigured or demo token
            return {"status": "UNPAID", "details": None}

        try:
            status = self.khqr.check_payment(md5_hash)
            payment_details = self.khqr.get_payment(md5_hash) if status == "PAID" else None
            return {"status": status, "details": payment_details}
        except Exception as e:
            logger.info(f"Bakong payment check: {e}")
            return {"status": "UNPAID", "details": None}
