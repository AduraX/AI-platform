import anyio
from fastapi import BackgroundTasks
from ingestion_service.routes import build_router
from python_common import AppSettings, PlatformError
from python_common.schemas import DocumentRequest
from starlette.requests import Request


def test_create_document_indexes_text_when_present(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    async def fake_index_document_text(**kwargs) -> int:
        calls.append(kwargs)
        return 2

    monkeypatch.setattr("ingestion_service.routes.index_document_text", fake_index_document_text)

    router = build_router(AppSettings(service_name="ingestion-service"))
    endpoint = next(route.endpoint for route in router.routes if route.path == "/v1/documents")
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/documents",
            "headers": [(b"x-tenant-id", b"tenant-a"), (b"x-user-id", b"user-123")],
        }
    )

    response = anyio.run(
        lambda: endpoint(
            request=request,
            payload=DocumentRequest(
                filename="policy.txt",
                content_type="text/plain",
                text="policy text",
            ),
            background_tasks=BackgroundTasks(),
        )
    )

    assert calls[0]["document_id"] == "doc-placeholder"
    assert calls[0]["text"] == "policy text"
    assert calls[0]["context"].tenant_id == "tenant-a"
    assert response.job_id == "job-0001"
    assert response.status == "completed"
    assert response.indexed_chunks == 2
    assert response.object_key == "documents/doc-placeholder/policy.txt"
    assert response.upload_url == (
        "http://localhost:9000/enterprise-ai/documents/doc-placeholder/policy.txt"
    )


def test_create_document_without_text_does_not_index(monkeypatch) -> None:
    async def fail_index_document_text(**kwargs) -> int:
        raise AssertionError("indexing should not be called")

    monkeypatch.setattr("ingestion_service.routes.index_document_text", fail_index_document_text)

    router = build_router(AppSettings(service_name="ingestion-service"))
    endpoint = next(route.endpoint for route in router.routes if route.path == "/v1/documents")
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/documents",
            "headers": [],
        }
    )

    response = anyio.run(
        lambda: endpoint(
            request=request,
            payload=DocumentRequest(filename="policy.pdf", content_type="application/pdf"),
            background_tasks=BackgroundTasks(),
        )
    )

    assert response.job_id == "job-0001"
    assert response.status == "completed"
    assert response.indexed_chunks == 0


def test_get_ingestion_job_returns_status(monkeypatch) -> None:
    async def fake_index_document_text(**kwargs) -> int:
        return 1

    monkeypatch.setattr("ingestion_service.routes.index_document_text", fake_index_document_text)

    router = build_router(AppSettings(service_name="ingestion-service"))
    create_endpoint = next(
        route.endpoint for route in router.routes if route.path == "/v1/documents"
    )
    get_endpoint = next(
        route.endpoint for route in router.routes if route.path == "/v1/ingestion-jobs/{job_id}"
    )
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/documents",
            "headers": [],
        }
    )

    created = anyio.run(
        lambda: create_endpoint(
            request=request,
            payload=DocumentRequest(
                filename="policy.txt",
                content_type="text/plain",
                text="policy text",
            ),
            background_tasks=BackgroundTasks(),
        )
    )
    response = get_endpoint(job_id=created.job_id)

    assert response.job_id == "job-0001"
    assert response.document_id == "doc-placeholder"
    assert response.status == "completed"
    assert response.indexed_chunks == 1


def test_get_ingestion_job_raises_for_unknown_job() -> None:
    router = build_router(AppSettings(service_name="ingestion-service"))
    endpoint = next(
        route.endpoint for route in router.routes if route.path == "/v1/ingestion-jobs/{job_id}"
    )

    try:
        endpoint(job_id="job-missing")
    except PlatformError as exc:
        assert exc.code == "ingestion_job_not_found"
        assert exc.status_code == 404
    else:
        raise AssertionError("expected PlatformError")


def test_create_document_can_enqueue_background_processing(monkeypatch) -> None:
    async def fail_index_document_text(**kwargs) -> int:
        raise AssertionError("indexing should be deferred")

    monkeypatch.setattr("ingestion_service.routes.index_document_text", fail_index_document_text)

    router = build_router(
        AppSettings(
            service_name="ingestion-service",
            ingestion_processing_mode="background",
        )
    )
    endpoint = next(route.endpoint for route in router.routes if route.path == "/v1/documents")
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/documents",
            "headers": [(b"x-tenant-id", b"tenant-a")],
        }
    )
    background_tasks = BackgroundTasks()

    response = anyio.run(
        lambda: endpoint(
            request=request,
            payload=DocumentRequest(
                filename="policy.txt",
                content_type="text/plain",
                text="policy text",
            ),
            background_tasks=background_tasks,
        )
    )

    assert response.status == "pending"
    assert len(background_tasks.tasks) == 1


def test_create_document_redis_background_mode_defers_to_worker(monkeypatch) -> None:
    from ingestion_service.queue import InMemoryIngestionQueue

    async def fail_index_document_text(**kwargs) -> int:
        raise AssertionError("indexing should be handled by the durable worker")

    monkeypatch.setattr("ingestion_service.routes.index_document_text", fail_index_document_text)
    monkeypatch.setattr(
        "ingestion_service.routes.create_ingestion_queue",
        lambda settings: InMemoryIngestionQueue(),
    )

    router = build_router(
        AppSettings(
            service_name="ingestion-service",
            ingestion_processing_mode="background",
            ingestion_queue_backend="redis",
        )
    )
    endpoint = next(route.endpoint for route in router.routes if route.path == "/v1/documents")
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/documents",
            "headers": [(b"x-tenant-id", b"tenant-a")],
        }
    )
    background_tasks = BackgroundTasks()

    response = anyio.run(
        lambda: endpoint(
            request=request,
            payload=DocumentRequest(
                filename="policy.txt",
                content_type="text/plain",
                text="policy text",
            ),
            background_tasks=background_tasks,
        )
    )

    assert response.status == "pending"
    assert len(background_tasks.tasks) == 0
