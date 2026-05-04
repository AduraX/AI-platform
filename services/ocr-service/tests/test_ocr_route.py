"""Tests for the OCR service endpoint."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from ocr_service.extraction import ExtractionResult


def _make_app():
    """Create a fresh app instance for testing."""
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path

    module_path = Path(__file__).resolve().parents[1] / "ocr_service" / "main.py"
    spec = spec_from_file_location("ocr_service_main", module_path)
    module = module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module.app


@patch("ocr_service.routes.StorageClient")
@patch("ocr_service.routes.extract_text")
def test_ocr_returns_extracted_text(mock_extract, mock_storage_cls):
    mock_storage = MagicMock()
    mock_storage.download.return_value = b"file contents"
    mock_storage_cls.return_value = mock_storage

    mock_extract.return_value = ExtractionResult(
        text="Extracted document text",
        content_type="application/pdf",
        page_count=3,
        tables=["| col | val |"],
    )

    app = _make_app()
    client = TestClient(app)
    resp = client.post("/internal/ocr", json={
        "document_id": "doc-abc123",
        "object_key": "documents/doc-abc123/report.pdf",
    })

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "processed"
    assert body["extracted_text"] == "Extracted document text"
    assert body["document_id"] == "doc-abc123"
    assert body["content_type"] == "application/pdf"
    assert body["page_count"] == 3
    assert body["tables"] == ["| col | val |"]

    mock_storage.download.assert_called_once_with("documents/doc-abc123/report.pdf")
    mock_extract.assert_called_once_with(b"file contents", "documents/doc-abc123/report.pdf")


@patch("ocr_service.routes.StorageClient")
def test_ocr_handles_download_failure(mock_storage_cls):
    mock_storage = MagicMock()
    mock_storage.download.side_effect = Exception("Connection refused")
    mock_storage_cls.return_value = mock_storage

    app = _make_app()
    client = TestClient(app)
    resp = client.post("/internal/ocr", json={
        "document_id": "doc-fail",
        "object_key": "documents/doc-fail/missing.pdf",
    })

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failed"
    assert body["extracted_text"] == ""


@patch("ocr_service.routes.StorageClient")
@patch("ocr_service.routes.extract_text")
def test_ocr_handles_extraction_failure(mock_extract, mock_storage_cls):
    mock_storage = MagicMock()
    mock_storage.download.return_value = b"corrupt data"
    mock_storage_cls.return_value = mock_storage
    mock_extract.side_effect = Exception("Tesseract not found")

    app = _make_app()
    client = TestClient(app)
    resp = client.post("/internal/ocr", json={
        "document_id": "doc-corrupt",
        "object_key": "documents/doc-corrupt/bad.png",
    })

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failed"
    assert body["extracted_text"] == ""


def test_ocr_rejects_empty_document_id():
    app = _make_app()
    client = TestClient(app)
    resp = client.post("/internal/ocr", json={
        "document_id": "",
        "object_key": "documents/x/file.pdf",
    })
    assert resp.status_code == 422


def test_ocr_rejects_empty_object_key():
    app = _make_app()
    client = TestClient(app)
    resp = client.post("/internal/ocr", json={
        "document_id": "doc-123",
        "object_key": "",
    })
    assert resp.status_code == 422
