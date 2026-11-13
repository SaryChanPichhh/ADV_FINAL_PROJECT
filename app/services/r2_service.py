import os
import uuid
import boto3
from botocore.config import Config
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


class R2Service:
    def __init__(self):
        self.account_id = os.getenv("R2_ACCOUNT_ID")
        self.bucket_name = os.getenv("R2_BUCKET_NAME")
        self.public_url = os.getenv("R2_PUBLIC_URL", "").rstrip("/")
        self.access_key = os.getenv("R2_ACCESS_KEY_ID")
        self.secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

        self.is_configured = bool(
            self.account_id
            and self.bucket_name
            and self.access_key
            and self.secret_key
            and not self.account_id.startswith("your_")
        )

        if self.is_configured:
            self.s3_client = boto3.client(
                service_name="s3",
                endpoint_url=f"https://{self.account_id}.r2.cloudflarestorage.com",
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name="auto",
                config=Config(signature_version="s3v4"),
            )
        else:
            self.s3_client = None

    @staticmethod
    def is_allowed_file(filename: str) -> bool:
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    def upload_product_image(self, file_storage) -> dict:
        if not file_storage or not file_storage.filename:
            raise ValueError("No file provided")
        if not self.is_allowed_file(file_storage.filename):
            raise ValueError("Invalid image format. Allowed: png, jpg, jpeg, webp")

        clean_name = secure_filename(file_storage.filename)
        unique_prefix = uuid.uuid4().hex
        object_key = f"products/{unique_prefix}-{clean_name}"

        # If Cloudflare R2 is configured, upload to R2
        if self.is_configured and self.s3_client:
            self.s3_client.upload_fileobj(
                Fileobj=file_storage,
                Bucket=self.bucket_name,
                Key=object_key,
                ExtraArgs={
                    "ContentType": file_storage.content_type or "image/jpeg",
                    "CacheControl": "public, max-age=31536000",
                },
            )
            image_url = f"{self.public_url}/{object_key}" if self.public_url else f"/{object_key}"
            return {
                "image_url": image_url,
                "image_key": object_key,
            }

        # Local storage fallback for local development without R2
        upload_folder = current_app.config.get("UPLOAD_FOLDER")
        if not upload_folder:
            upload_folder = os.path.join(current_app.root_path, "static", "uploads")
        os.makedirs(upload_folder, exist_ok=True)

        local_filename = f"{unique_prefix}-{clean_name}"
        local_path = os.path.join(upload_folder, local_filename)
        file_storage.seek(0)
        file_storage.save(local_path)

        return {
            "image_url": f"/static/uploads/{local_filename}",
            "image_key": f"local:{local_filename}",
        }

    def delete_product_image(self, object_key: str) -> None:
        if not object_key:
            return

        if object_key.startswith("local:"):
            # Local fallback deletion
            local_filename = object_key.replace("local:", "", 1)
            upload_folder = current_app.config.get("UPLOAD_FOLDER")
            if upload_folder:
                local_path = os.path.join(upload_folder, local_filename)
                if os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                    except OSError:
                        pass
            return

        if self.is_configured and self.s3_client:
            try:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_key)
            except Exception:
                pass
