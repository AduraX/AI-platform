"""Shared test fixtures for the enterprise AI platform."""
from unittest.mock import AsyncMock

import pytest
from python_common.config.settings import AppSettings
from python_common.schemas.auth import RequestContext


@pytest.fixture
def test_settings() -> AppSettings:
    """Provide default test settings."""
    return AppSettings(
        service_name="test-service",
        environment="test",
        auth_enabled=False,
        embedding_provider="deterministic",
        ingestion_job_store_backend="memory",
        ingestion_queue_backend="memory",
        ingestion_processing_mode="sync",
    )


@pytest.fixture
def test_context() -> RequestContext:
    """Provide a test request context."""
    return RequestContext(
        tenant_id="test-tenant",
        user_id="test-user@example.com",
        roles=["user"],
        request_id="test-request-001",
    )


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Provide a mock async HTTP client."""
    client = AsyncMock()
    client.post = AsyncMock()
    client.get = AsyncMock()
    return client
