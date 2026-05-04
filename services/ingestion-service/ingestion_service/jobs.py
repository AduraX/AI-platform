from dataclasses import dataclass
from typing import Literal, Protocol

from python_common import AppSettings
from python_common.schemas import RequestContext

IngestionJobStatus = Literal["pending", "completed", "failed"]


@dataclass
class IngestionJob:
    job_id: str
    document_id: str
    status: IngestionJobStatus
    filename: str = ""
    content_type: str = ""
    tenant_id: str = "default"
    user_id: str = "anonymous"
    source_text: str | None = None
    indexed_chunks: int = 0
    error: str | None = None


class IngestionJobStore(Protocol):
    def create(
        self,
        *,
        document_id: str,
        filename: str,
        content_type: str,
        context: RequestContext,
        source_text: str | None,
    ) -> IngestionJob:
        """Create a document metadata record and ingestion job."""

    def complete(self, *, job_id: str, indexed_chunks: int) -> IngestionJob:
        """Mark a job as completed."""

    def fail(self, *, job_id: str, error: str) -> IngestionJob:
        """Mark a job as failed."""

    def get(self, *, job_id: str) -> IngestionJob | None:
        """Return a job by ID."""


class InMemoryIngestionJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, IngestionJob] = {}

    def create(
        self,
        *,
        document_id: str,
        filename: str,
        content_type: str,
        context: RequestContext,
        source_text: str | None,
    ) -> IngestionJob:
        job_id = f"job-{len(self._jobs) + 1:04d}"
        job = IngestionJob(
            job_id=job_id,
            document_id=document_id,
            filename=filename,
            content_type=content_type,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            source_text=source_text,
            status="pending",
        )
        self._jobs[job_id] = job
        return job

    def complete(self, *, job_id: str, indexed_chunks: int) -> IngestionJob:
        job = self._jobs[job_id]
        job.status = "completed"
        job.indexed_chunks = indexed_chunks
        job.error = None
        return job

    def fail(self, *, job_id: str, error: str) -> IngestionJob:
        job = self._jobs[job_id]
        job.status = "failed"
        job.error = error
        return job

    def get(self, *, job_id: str) -> IngestionJob | None:
        return self._jobs.get(job_id)


class PostgresIngestionJobStore:
    def __init__(self, *, settings: AppSettings) -> None:
        from python_common.db import get_conninfo
        self.conninfo = get_conninfo(
            host=settings.postgres_host,
            port=settings.postgres_port,
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
        )

    def create(
        self,
        *,
        document_id: str,
        filename: str,
        content_type: str,
        context: RequestContext,
        source_text: str | None,
    ) -> IngestionJob:
        from python_common.db import get_connection

        job_id = f"job-{document_id}"
        with get_connection(self.conninfo) as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                    insert into documents (document_id, filename, content_type)
                    values (%s, %s, %s)
                    on conflict (document_id) do update
                    set filename = excluded.filename,
                        content_type = excluded.content_type
                    """,
                (document_id, filename, content_type),
            )
            cursor.execute(
                """
                    insert into ingestion_jobs (
                        job_id,
                        document_id,
                        status,
                        tenant_id,
                        user_id,
                        source_text
                    )
                    values (%s, %s, 'pending', %s, %s, %s)
                    """,
                (job_id, document_id, context.tenant_id, context.user_id, source_text),
            )
        return IngestionJob(
            job_id=job_id,
            document_id=document_id,
            filename=filename,
            content_type=content_type,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            source_text=source_text,
            status="pending",
        )

    def complete(self, *, job_id: str, indexed_chunks: int) -> IngestionJob:
        return self._update(job_id=job_id, status="completed", indexed_chunks=indexed_chunks)

    def fail(self, *, job_id: str, error: str) -> IngestionJob:
        return self._update(job_id=job_id, status="failed", error=error)

    def get(self, *, job_id: str) -> IngestionJob | None:
        from python_common.db import get_connection

        with get_connection(self.conninfo) as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                    select j.job_id,
                           j.document_id,
                           j.status,
                           j.indexed_chunks,
                           j.error,
                           j.tenant_id,
                           j.user_id,
                           j.source_text,
                           d.filename,
                           d.content_type
                    from ingestion_jobs j
                    join documents d on d.document_id = j.document_id
                    where j.job_id = %s
                    """,
                (job_id,),
            )
            row = cursor.fetchone()

        return _job_from_row(row) if row else None

    def _update(
        self,
        *,
        job_id: str,
        status: IngestionJobStatus,
        indexed_chunks: int = 0,
        error: str | None = None,
    ) -> IngestionJob:
        from python_common.db import get_connection

        with get_connection(self.conninfo) as conn, conn.cursor() as cursor:
            cursor.execute(
                """
                    update ingestion_jobs
                    set status = %s,
                        indexed_chunks = %s,
                        error = %s,
                        updated_at = now()
                    where job_id = %s
                    """,
                (status, indexed_chunks, error, job_id),
            )
        job = self.get(job_id=job_id)
        if job is None:
            raise KeyError(job_id)
        return job


def _job_from_row(row: tuple[object, ...]) -> IngestionJob:
    return IngestionJob(
        job_id=str(row[0]),
        document_id=str(row[1]),
        status=row[2],  # type: ignore[arg-type]
        indexed_chunks=int(row[3]),
        error=str(row[4]) if row[4] is not None else None,
        tenant_id=str(row[5]),
        user_id=str(row[6]),
        source_text=str(row[7]) if row[7] is not None else None,
        filename=str(row[8]),
        content_type=str(row[9]),
    )


def create_ingestion_job_store(settings: AppSettings) -> IngestionJobStore:
    if settings.ingestion_job_store_backend == "postgres":
        return PostgresIngestionJobStore(settings=settings)

    return InMemoryIngestionJobStore()
