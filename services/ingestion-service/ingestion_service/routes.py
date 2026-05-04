import uuid

from fastapi import APIRouter, BackgroundTasks, File, Form, Request, UploadFile
from python_common import AppSettings, PlatformError
from python_common.schemas import (
    DocumentCreatedResponse,
    DocumentRequest,
    IngestionJobResponse,
    RequestContext,
)
from python_common.web import request_context_from_headers

from ingestion_service.jobs import IngestionJob, IngestionJobStore, create_ingestion_job_store
from ingestion_service.queue import IngestionQueueItem, create_ingestion_queue
from ingestion_service.storage import document_object_key, upload_url
from ingestion_service.workflow import index_document_text


def _job_response(job: IngestionJob) -> IngestionJobResponse:
    return IngestionJobResponse(
        service="ingestion-service",
        job_id=job.job_id,
        document_id=job.document_id,
        status=job.status,
        indexed_chunks=job.indexed_chunks,
        error=job.error,
    )


async def _process_document_text(
    *,
    settings: AppSettings,
    jobs: IngestionJobStore,
    job_id: str,
    document_id: str,
    text: str,
    context: RequestContext,
) -> IngestionJob:
    try:
        indexed_chunks = await index_document_text(
            settings=settings,
            document_id=document_id,
            text=text,
            context=context,
        )
        return jobs.complete(job_id=job_id, indexed_chunks=indexed_chunks)
    except Exception as exc:
        jobs.fail(job_id=job_id, error=str(exc))
        raise


def build_router(settings: AppSettings, job_store: IngestionJobStore | None = None) -> APIRouter:
    router = APIRouter(tags=["documents"])
    jobs = job_store or create_ingestion_job_store(settings)
    queue = create_ingestion_queue(settings)

    @router.post("/v1/documents", response_model=DocumentCreatedResponse)
    async def create_document(
        request: Request,
        payload: DocumentRequest,
        background_tasks: BackgroundTasks,
    ) -> DocumentCreatedResponse:
        document_id = "doc-placeholder"
        context = request_context_from_headers(request)
        job = jobs.create(
            document_id=document_id,
            filename=payload.filename,
            content_type=payload.content_type,
            context=context,
            source_text=payload.text,
        )
        object_key = document_object_key(document_id=document_id, filename=payload.filename)

        if payload.text and settings.ingestion_processing_mode == "background":
            queue.enqueue(IngestionQueueItem(job_id=job.job_id, document_id=document_id))
            if settings.ingestion_queue_backend == "memory":
                background_tasks.add_task(
                    _process_document_text,
                    settings=settings,
                    jobs=jobs,
                    job_id=job.job_id,
                    document_id=document_id,
                    text=payload.text,
                    context=context,
                )
        elif payload.text:
            job = await _process_document_text(
                settings=settings,
                jobs=jobs,
                job_id=job.job_id,
                document_id=document_id,
                text=payload.text,
                context=context,
            )
        else:
            job = jobs.complete(job_id=job.job_id, indexed_chunks=0)

        return DocumentCreatedResponse(
            service="ingestion-service",
            document_id=document_id,
            filename=payload.filename,
            job_id=job.job_id,
            status=job.status,
            indexed_chunks=job.indexed_chunks,
            object_key=object_key,
            upload_url=upload_url(settings=settings, object_key=object_key),
        )

    @router.post("/v1/documents:process", response_model=IngestionJobResponse)
    async def process_document(
        request: Request,
        payload: DocumentRequest,
    ) -> IngestionJobResponse:
        document_id = "doc-placeholder"
        context = request_context_from_headers(request)
        job = jobs.create(
            document_id=document_id,
            filename=payload.filename,
            content_type=payload.content_type,
            context=context,
            source_text=payload.text,
        )

        if payload.text:
            job = await _process_document_text(
                settings=settings,
                jobs=jobs,
                job_id=job.job_id,
                document_id=document_id,
                text=payload.text,
                context=context,
            )
        else:
            job = jobs.complete(job_id=job.job_id, indexed_chunks=0)

        return _job_response(job)

    @router.post("/v1/documents/upload", response_model=DocumentCreatedResponse)
    async def upload_document(
        request: Request,
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        content_type: str = Form(default="application/octet-stream"),
    ) -> DocumentCreatedResponse:
        """Upload a file for ingestion.

        The file is stored in object storage, then processed through the
        OCR -> chunk -> embed -> index pipeline.
        """
        context = request_context_from_headers(request)
        document_id = f"doc-{uuid.uuid4().hex[:12]}"
        filename = file.filename or "unnamed"
        object_key = f"documents/{document_id}/{filename}"

        # Store file in object storage
        from ingestion_service.object_store import ObjectStoreClient
        store = ObjectStoreClient(settings)
        store.upload_file(key=object_key, data=file.file, content_type=content_type)

        # Create job record
        job = jobs.create(
            document_id=document_id,
            filename=filename,
            content_type=content_type,
            context=context,
            source_text=None,
        )

        # Process: OCR -> chunk -> embed -> index
        async def process_uploaded_file():
            try:
                from ingestion_service.ocr_client import extract_text_from_document
                extracted_text = await extract_text_from_document(
                    settings=settings,
                    document_id=document_id,
                    object_key=object_key,
                    context=context,
                )
                if extracted_text:
                    indexed = await index_document_text(
                        settings=settings,
                        document_id=document_id,
                        text=extracted_text,
                        context=context,
                    )
                    jobs.complete(job_id=job.job_id, indexed_chunks=indexed)
                else:
                    jobs.complete(job_id=job.job_id, indexed_chunks=0)
            except Exception as exc:
                jobs.fail(job_id=job.job_id, error=str(exc))

        if settings.ingestion_processing_mode == "background":
            background_tasks.add_task(process_uploaded_file)
        else:
            await process_uploaded_file()

        # Re-fetch job status after processing
        updated_job = jobs.get(job_id=job.job_id) or job

        return DocumentCreatedResponse(
            service="ingestion-service",
            document_id=document_id,
            filename=filename,
            job_id=job.job_id,
            status=updated_job.status,
            indexed_chunks=updated_job.indexed_chunks,
            object_key=object_key,
            upload_url=upload_url(settings=settings, object_key=object_key),
        )

    @router.get("/v1/ingestion-jobs/{job_id}", response_model=IngestionJobResponse)
    def get_ingestion_job(job_id: str) -> IngestionJobResponse:
        job = jobs.get(job_id=job_id)
        if job is None:
            raise PlatformError(
                code="ingestion_job_not_found",
                message="Ingestion job was not found.",
                status_code=404,
                details={"job_id": job_id},
            )

        return _job_response(job)

    return router
