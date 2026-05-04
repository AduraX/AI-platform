from python_common import AppSettings
from python_common.schemas import RequestContext

from ingestion_service.jobs import IngestionJob, IngestionJobStore, create_ingestion_job_store
from ingestion_service.queue import IngestionQueue, create_ingestion_queue
from ingestion_service.workflow import index_document_text


async def process_next_ingestion_job(
    *,
    settings: AppSettings,
    jobs: IngestionJobStore | None = None,
    queue: IngestionQueue | None = None,
) -> IngestionJob | None:
    job_store = jobs or create_ingestion_job_store(settings)
    ingestion_queue = queue or create_ingestion_queue(settings)
    item = ingestion_queue.dequeue()
    if item is None:
        return None

    job = job_store.get(job_id=item.job_id)
    if job is None:
        return None

    try:
        if not job.source_text:
            return job_store.complete(job_id=job.job_id, indexed_chunks=0)

        indexed_chunks = await index_document_text(
            settings=settings,
            document_id=job.document_id,
            text=job.source_text,
            context=RequestContext(tenant_id=job.tenant_id, user_id=job.user_id),
        )
        return job_store.complete(job_id=job.job_id, indexed_chunks=indexed_chunks)
    except Exception as exc:
        return job_store.fail(job_id=job.job_id, error=str(exc))
