import anyio
from fastapi import Request, Response
from python_common import AppSettings, PlatformError
from python_common.web import create_service_app


def test_request_context_middleware_sets_response_headers() -> None:
    app = create_service_app(
        title="Test Service",
        version="0.1.0",
        settings=AppSettings(service_name="test-service"),
    )
    middleware = app.user_middleware[0]
    dispatch = middleware.kwargs["dispatch"]

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": [
            (b"x-tenant-id", b"tenant-a"),
            (b"x-user-id", b"user-123"),
            (b"x-roles", b"admin"),
            (b"x-request-id", b"req-001"),
        ],
    }
    request = Request(scope)

    async def call_next(_: Request) -> Response:
        return Response(status_code=200)

    response = anyio.run(lambda: dispatch(request, call_next))

    assert response.headers["x-tenant-id"] == "tenant-a"
    assert response.headers["x-user-id"] == "user-123"
    assert response.headers["x-roles"] == "admin"
    assert response.headers["x-request-id"] == "req-001"


def test_platform_error_includes_request_id() -> None:
    app = create_service_app(
        title="Test Service",
        version="0.1.0",
        settings=AppSettings(service_name="test-service"),
    )
    handler = app.exception_handlers[PlatformError]

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": [(b"x-request-id", b"req-999")],
    }
    request = Request(scope)
    exc = PlatformError(code="boom", message="failed", details={"reason": "test"})

    response = anyio.run(lambda: handler(request, exc))

    assert response.status_code == 500
    assert b'"request_id":"req-999"' in response.body
