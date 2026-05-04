from python_common.web import (
    ensure_request_id,
    request_context_from_headers,
    request_context_to_headers,
)
from starlette.requests import Request


def test_request_context_header_round_trip() -> None:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/v1/chat",
        "headers": [
            (b"x-tenant-id", b"tenant-a"),
            (b"x-user-id", b"user-123"),
            (b"x-roles", b"admin,analyst"),
            (b"x-request-id", b"req-001"),
        ],
    }
    request = Request(scope)

    context = request_context_from_headers(request)

    assert context.tenant_id == "tenant-a"
    assert context.user_id == "user-123"
    assert context.roles == ["admin", "analyst"]
    assert request_context_to_headers(context)["x-request-id"] == "req-001"


def test_request_context_generates_missing_request_id() -> None:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/health",
        "headers": [],
    }
    request = Request(scope)

    context = request_context_from_headers(request)

    assert context.request_id != "unknown"
    assert len(context.request_id) > 10


def test_ensure_request_id_keeps_existing_value() -> None:
    assert ensure_request_id("req-123") == "req-123"
