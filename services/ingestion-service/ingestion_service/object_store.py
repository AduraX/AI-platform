"""S3-compatible object storage client for MinIO."""
from __future__ import annotations

from typing import BinaryIO

from python_common.config.settings import AppSettings


class ObjectStoreClient:
    """Thin wrapper around boto3 S3 client for MinIO."""

    def __init__(self, settings: AppSettings) -> None:
        import boto3
        from botocore.config import Config

        self.bucket = settings.object_storage_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.object_storage_endpoint,
            aws_access_key_id=settings.object_storage_access_key,
            aws_secret_access_key=settings.object_storage_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            self.client.create_bucket(Bucket=self.bucket)

    def upload_file(self, *, key: str, data: BinaryIO, content_type: str) -> str:
        """Upload a file and return the object key."""
        self.client.upload_fileobj(
            data,
            self.bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return key

    def download_file(self, *, key: str) -> bytes:
        """Download a file and return its contents."""
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def generate_presigned_url(self, *, key: str, expires_in: int = 3600) -> str:
        """Generate a pre-signed URL for direct upload."""
        return self.client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )
