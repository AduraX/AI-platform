from urllib.parse import quote

from python_common import AppSettings


def document_object_key(*, document_id: str, filename: str) -> str:
    safe_filename = quote(filename.strip(), safe="")
    return f"documents/{document_id}/{safe_filename}"


def upload_url(*, settings: AppSettings, object_key: str) -> str:
    endpoint = settings.object_storage_endpoint.rstrip("/")
    bucket = quote(settings.object_storage_bucket.strip("/"), safe="")
    return f"{endpoint}/{bucket}/{object_key}"
