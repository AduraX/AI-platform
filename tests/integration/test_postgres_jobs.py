"""Integration tests for PostgreSQL-backed ingestion job store.

Requires: docker compose up -d postgres
Run with: uv run pytest -m integration tests/integration/test_postgres_jobs.py
"""
import pytest
from python_common.config.settings import AppSettings
from python_common.schemas.auth import RequestContext

pytestmark = pytest.mark.integration


@pytest.fixture
def pg_settings() -> AppSettings:
    return AppSettings(
        service_name="integration-test",
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="enterprise_ai",
        postgres_user="enterprise_ai",
        postgres_password="enterprise_ai",
        ingestion_job_store_backend="postgres",
    )


@pytest.fixture
def pg_job_store(pg_settings):
    from ingestion_service.migrations import run_migrations
    run_migrations(settings=pg_settings)

    from ingestion_service.jobs import PostgresIngestionJobStore
    return PostgresIngestionJobStore(settings=pg_settings)


@pytest.fixture
def test_context() -> RequestContext:
    return RequestContext(
        tenant_id="integration-tenant",
        user_id="test@integration.com",
        roles=["admin"],
        request_id="integration-test-001",
    )


def test_create_and_get_job(pg_job_store, test_context):
    job = pg_job_store.create(
        document_id="int-doc-001",
        filename="test-doc.pdf",
        content_type="application/pdf",
        context=test_context,
        source_text="Integration test content.",
    )

    assert job.job_id is not None
    assert job.status == "pending"
    assert job.tenant_id == "integration-tenant"

    retrieved = pg_job_store.get(job_id=job.job_id)
    assert retrieved is not None
    assert retrieved.document_id == "int-doc-001"
    assert retrieved.filename == "test-doc.pdf"


def test_complete_job(pg_job_store, test_context):
    job = pg_job_store.create(
        document_id="int-doc-002",
        filename="complete-test.pdf",
        content_type="application/pdf",
        context=test_context,
        source_text=None,
    )

    completed = pg_job_store.complete(job_id=job.job_id, indexed_chunks=5)
    assert completed.status == "completed"
    assert completed.indexed_chunks == 5


def test_fail_job(pg_job_store, test_context):
    job = pg_job_store.create(
        document_id="int-doc-003",
        filename="fail-test.pdf",
        content_type="application/pdf",
        context=test_context,
        source_text=None,
    )

    failed = pg_job_store.fail(job_id=job.job_id, error="Connection timeout")
    assert failed.status == "failed"
    assert failed.error == "Connection timeout"


def test_get_nonexistent_job(pg_job_store):
    result = pg_job_store.get(job_id="nonexistent-job-id")
    assert result is None
