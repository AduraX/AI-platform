import anyio
from ingestion_service.jobs import InMemoryIngestionJobStore
from ingestion_service.queue import IngestionQueueItem, InMemoryIngestionQueue
from ingestion_service.worker import process_next_ingestion_job
from python_common import AppSettings
from python_common.schemas import RequestContext


def test_worker_returns_none_when_queue_is_empty() -> None:
    result = anyio.run(
        lambda: process_next_ingestion_job(
            settings=AppSettings(service_name="ingestion-service"),
            jobs=InMemoryIngestionJobStore(),
            queue=InMemoryIngestionQueue(),
        )
    )

    assert result is None


def test_worker_processes_queued_job(monkeypatch) -> None:
    async def fake_index_document_text(**kwargs) -> int:
        assert kwargs["document_id"] == "doc-1"
        assert kwargs["text"] == "policy text"
        assert kwargs["context"].tenant_id == "tenant-a"
        return 2

    monkeypatch.setattr("ingestion_service.worker.index_document_text", fake_index_document_text)

    jobs = InMemoryIngestionJobStore()
    job = jobs.create(
        document_id="doc-1",
        filename="policy.txt",
        content_type="text/plain",
        context=RequestContext(tenant_id="tenant-a", user_id="user-1"),
        source_text="policy text",
    )
    queue = InMemoryIngestionQueue()
    queue.enqueue(IngestionQueueItem(job_id=job.job_id, document_id=job.document_id))

    result = anyio.run(
        lambda: process_next_ingestion_job(
            settings=AppSettings(service_name="ingestion-service"),
            jobs=jobs,
            queue=queue,
        )
    )

    assert result is not None
    assert result.status == "completed"
    assert result.indexed_chunks == 2
