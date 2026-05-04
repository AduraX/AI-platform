"""Shared fixtures for RAG service tests."""
import pytest
from python_common.config.settings import AppSettings


@pytest.fixture
def rag_settings() -> AppSettings:
    return AppSettings(
        service_name="rag-service",
        environment="test",
        auth_enabled=False,
        vector_store_backend="qdrant",
    )
