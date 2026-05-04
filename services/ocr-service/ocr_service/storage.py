"""Object storage client for downloading files to process."""
from __future__ import annotations

from python_common.config.settings import AppSettings


class StorageClient:
    """Download files from S3-compatible object storage (MinIO)."""

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

    def download(self, object_key: str) -> bytes:
        """Download an object and return its raw bytes."""
        response = self.client.get_object(Bucket=self.bucket, Key=object_key)
        return response["Body"].read()
