from ingestion_service.storage import document_object_key, upload_url
from python_common import AppSettings


def test_document_object_key_escapes_filename() -> None:
    assert (
        document_object_key(document_id="doc-1", filename="Policy Final.pdf")
        == "documents/doc-1/Policy%20Final.pdf"
    )


def test_upload_url_uses_configured_bucket() -> None:
    settings = AppSettings(
        service_name="ingestion-service",
        object_storage_endpoint="http://minio:9000/",
        object_storage_bucket="enterprise-ai",
    )

    assert (
        upload_url(settings=settings, object_key="documents/doc-1/policy.txt")
        == "http://minio:9000/enterprise-ai/documents/doc-1/policy.txt"
    )
