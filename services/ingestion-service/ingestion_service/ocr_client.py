"""Client for the OCR service."""
from __future__ import annotations

from python_common.config.settings import AppSettings
from python_common.schemas import RequestContext
from python_common.web import post_json, request_context_to_headers


async def extract_text_from_document(
    *,
    settings: AppSettings,
    document_id: str,
    object_key: str,
    context: RequestContext,
) -> str:
    """Send a document to the OCR service and return extracted text."""
    response = await post_json(
        service="ocr-service",
        base_url=settings.ocr_service_base_url,
        path="/internal/ocr",
        payload={"document_id": document_id, "object_key": object_key},
        headers=request_context_to_headers(context),
        timeout=settings.request_timeout_seconds * 3,  # OCR takes longer
        retry_count=1,
    )
    return response.get("extracted_text", "")
