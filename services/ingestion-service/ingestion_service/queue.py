from dataclasses import dataclass
from typing import Protocol

from python_common import AppSettings


@dataclass
class IngestionQueueItem:
    job_id: str
    document_id: str


class IngestionQueue(Protocol):
    def enqueue(self, item: IngestionQueueItem) -> None:
        """Enqueue an ingestion job for worker processing."""

    def dequeue(self) -> IngestionQueueItem | None:
        """Return the next queued ingestion job."""


class InMemoryIngestionQueue:
    def __init__(self) -> None:
        self.items: list[IngestionQueueItem] = []

    def enqueue(self, item: IngestionQueueItem) -> None:
        self.items.append(item)

    def dequeue(self) -> IngestionQueueItem | None:
        if not self.items:
            return None

        return self.items.pop(0)


class RedisIngestionQueue:
    queue_name = "ingestion_jobs"

    def __init__(self, *, settings: AppSettings) -> None:
        self.settings = settings

    def enqueue(self, item: IngestionQueueItem) -> None:
        import redis

        client = redis.Redis(host=self.settings.redis_host, port=self.settings.redis_port)
        client.rpush(self.queue_name, f"{item.job_id}:{item.document_id}")

    def dequeue(self) -> IngestionQueueItem | None:
        import redis

        client = redis.Redis(host=self.settings.redis_host, port=self.settings.redis_port)
        raw_item = client.lpop(self.queue_name)
        if raw_item is None:
            return None

        value = raw_item.decode("utf-8") if isinstance(raw_item, bytes) else str(raw_item)
        job_id, document_id = value.split(":", maxsplit=1)
        return IngestionQueueItem(job_id=job_id, document_id=document_id)


def create_ingestion_queue(settings: AppSettings) -> IngestionQueue:
    if settings.ingestion_queue_backend == "redis":
        return RedisIngestionQueue(settings=settings)

    return InMemoryIngestionQueue()
