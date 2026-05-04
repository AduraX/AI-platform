import logging

from fastapi import APIRouter, Depends
from python_common import AppSettings
from python_common.schemas import OcrRequest, OcrResponse

from ocr_service.extraction import extract_text
from ocr_service.storage import StorageClient

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ocr"])


def _get_settings() -> AppSettings:
    from ocr_service.main import settings

    return settings


@router.post("/internal/ocr")
def run_ocr(
    payload: OcrRequest,
    settings: AppSettings = Depends(_get_settings),
) -> OcrResponse:
    """Download a document from object storage and extract text."""
    try:
        storage = StorageClient(settings)
        data = storage.download(payload.object_key)
    except Exception:
        logger.exception("Failed to download %s from object storage", payload.object_key)
        return OcrResponse(
            status="failed",
            document_id=payload.document_id,
            object_key=payload.object_key,
            extracted_text="",
        )

    try:
        result = extract_text(data, payload.object_key)
    except Exception:
        logger.exception("Failed to extract text from %s", payload.object_key)
        return OcrResponse(
            status="failed",
            document_id=payload.document_id,
            object_key=payload.object_key,
            extracted_text="",
        )

    return OcrResponse(
        status="processed",
        document_id=payload.document_id,
        object_key=payload.object_key,
        extracted_text=result.text,
        content_type=result.content_type,
        page_count=result.page_count,
        tables=result.tables,
    )
