# Ingestion Service

Document intake, job creation, version tracking, and worker orchestration.

`POST /v1/documents` accepts document metadata and optional `text`. When text is
provided, the service splits it into chunks, requests embeddings from
`model-router`, and sends embedded chunks to `rag-service` for vector indexing.

Current endpoints:

- `POST /v1/documents`: registers a document and creates an ingestion job
- `POST /v1/documents:process`: runs the ingestion processing contract directly
- `GET /v1/ingestion-jobs/{job_id}`: returns the current ingestion job status

Document creation responses include an object-storage `object_key` and local
upload URL derived from `OBJECT_STORAGE_ENDPOINT` and `OBJECT_STORAGE_BUCKET`.

Job state uses `INGESTION_JOB_STORE_BACKEND=memory` by default. Set
`INGESTION_JOB_STORE_BACKEND=postgres` after applying the SQL migrations in
`services/ingestion-service/migrations`.

Run migrations:

```bash
cd services/ingestion-service && uv run python -m ingestion_service.migrations
```

Processing runs synchronously by default. Set `INGESTION_PROCESSING_MODE=background`
to return a pending job immediately and process inline text in a FastAPI background
task.

Queueing uses `INGESTION_QUEUE_BACKEND=memory` by default. Set
`INGESTION_QUEUE_BACKEND=redis` to enqueue background jobs onto Redis for a future
durable worker.

The worker contract is implemented in `ingestion_service.worker`. It dequeues a
job, reloads persisted job input, runs chunk/embed/index, and updates job status.

Local run:

```bash
cd services/ingestion-service && uv run uvicorn ingestion_service.main:app --reload --port 8004
```
