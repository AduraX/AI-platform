"""Tests for the file upload endpoint."""
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from ingestion_service.jobs import InMemoryIngestionJobStore
from ingestion_service.routes import build_router
from python_common.config.settings import AppSettings


@pytest.fixture
def upload_app():
    settings = AppSettings(
        service_name="ingestion-service",
        environment="test",
        embedding_provider="deterministic",
        ingestion_processing_mode="sync",
    )
    job_store = InMemoryIngestionJobStore()
    app = FastAPI()
    app.include_router(build_router(settings, job_store=job_store))
    return app


def test_upload_endpoint_accepts_file(upload_app):
    """Test that the upload endpoint accepts a file and creates a job."""
    mock_store = MagicMock()

    with (
        patch("ingestion_service.object_store.ObjectStoreClient", return_value=mock_store),
        patch(
            "ingestion_service.ocr_client.extract_text_from_document",
            new_callable=AsyncMock,
            return_value="Extracted text.",
        ),
        patch(
            "ingestion_service.routes.index_document_text",
            new_callable=AsyncMock,
            return_value=1,
        ),
    ):

        client = TestClient(upload_app)
        response = client.post(
            "/v1/documents/upload",
            files={"file": ("test.pdf", io.BytesIO(b"fake pdf content"), "application/pdf")},
            data={"content_type": "application/pdf"},
            headers={"x-tenant-id": "test-tenant", "x-user-id": "test@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.pdf"
        assert data["status"] in ("completed", "pending")
        assert "job_id" in data
        assert "object_key" in data
        mock_store.upload_file.assert_called_once()
