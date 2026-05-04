"""Shared fixtures for ingestion service tests."""

import pytest
from ingestion_service.jobs import InMemoryIngestionJobStore
from python_common.config.settings import AppSettings


@pytest.fixture
def ingestion_settings() -> AppSettings:
    return AppSettings(
        service_name="ingestion-service",
        environment="test",
        auth_enabled=False,
        embedding_provider="deterministic",
        ingestion_job_store_backend="memory",
        ingestion_queue_backend="memory",
        ingestion_processing_mode="sync",
    )


@pytest.fixture
def job_store() -> InMemoryIngestionJobStore:
    return InMemoryIngestionJobStore()
