"""Integration tests for Redis-backed ingestion queue.

Requires: docker compose up -d redis
Run with: uv run pytest -m integration tests/integration/test_redis_queue.py
"""
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def redis_queue():
    from ingestion_service.queue import RedisIngestionQueue
    queue = RedisIngestionQueue(host="localhost", port=6379)
    # Clean up any leftover test data
    queue._redis.delete("ingestion:jobs")
    yield queue
    queue._redis.delete("ingestion:jobs")


def test_enqueue_and_dequeue(redis_queue):
    from ingestion_service.queue import IngestionQueueItem

    item = IngestionQueueItem(job_id="redis-job-001", document_id="redis-doc-001")
    redis_queue.enqueue(item)

    dequeued = redis_queue.dequeue()
    assert dequeued is not None
    assert dequeued.job_id == "redis-job-001"
    assert dequeued.document_id == "redis-doc-001"


def test_dequeue_empty_queue(redis_queue):
    result = redis_queue.dequeue()
    assert result is None


def test_fifo_order(redis_queue):
    from ingestion_service.queue import IngestionQueueItem

    for i in range(3):
        redis_queue.enqueue(IngestionQueueItem(job_id=f"order-{i}", document_id=f"doc-{i}"))

    for i in range(3):
        item = redis_queue.dequeue()
        assert item is not None
        assert item.job_id == f"order-{i}"
