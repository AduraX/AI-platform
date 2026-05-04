from ingestion_service.queue import (
    IngestionQueueItem,
    InMemoryIngestionQueue,
    RedisIngestionQueue,
    create_ingestion_queue,
)
from python_common import AppSettings


def test_memory_queue_records_items() -> None:
    queue = InMemoryIngestionQueue()
    item = IngestionQueueItem(job_id="job-1", document_id="doc-1")

    queue.enqueue(item)

    assert queue.dequeue() == item
    assert queue.dequeue() is None


def test_create_queue_defaults_to_memory() -> None:
    queue = create_ingestion_queue(AppSettings(service_name="ingestion-service"))

    assert isinstance(queue, InMemoryIngestionQueue)


def test_create_queue_accepts_redis() -> None:
    queue = create_ingestion_queue(
        AppSettings(service_name="ingestion-service", ingestion_queue_backend="redis")
    )

    assert isinstance(queue, RedisIngestionQueue)
