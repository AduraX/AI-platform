from ingestion_service.jobs import (
    InMemoryIngestionJobStore,
    PostgresIngestionJobStore,
    create_ingestion_job_store,
)
from python_common import AppSettings
from python_common.schemas import RequestContext


def test_in_memory_job_store_tracks_state_transitions() -> None:
    store = InMemoryIngestionJobStore()

    created = store.create(
        document_id="doc-1",
        filename="policy.txt",
        content_type="text/plain",
        context=RequestContext(tenant_id="tenant-a", user_id="user-1"),
        source_text="policy text",
    )
    completed = store.complete(job_id=created.job_id, indexed_chunks=3)

    assert created.job_id == "job-0001"
    assert created.tenant_id == "tenant-a"
    assert created.user_id == "user-1"
    assert created.source_text == "policy text"
    assert completed.status == "completed"
    assert completed.indexed_chunks == 3
    assert store.get(job_id=created.job_id) == completed


def test_create_job_store_defaults_to_memory() -> None:
    store = create_ingestion_job_store(AppSettings(service_name="ingestion-service"))

    assert isinstance(store, InMemoryIngestionJobStore)


def test_create_job_store_accepts_postgres() -> None:
    store = create_ingestion_job_store(
        AppSettings(
            service_name="ingestion-service",
            ingestion_job_store_backend="postgres",
        )
    )

    assert isinstance(store, PostgresIngestionJobStore)
