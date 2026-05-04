import anyio
import httpx
from python_common import UpstreamServiceError
from python_common.schemas import ChatRequest, ChatResponse, RetrieveRequest, RetrieveResponse
from python_common.web import post_json_model


def test_post_json_model_retries_then_succeeds(monkeypatch) -> None:
    call_count = {"value": 0}

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"service": "chat-service", "reply": "accepted: hello", "sources": []}

    class DummyAsyncClient:
        def __init__(self, *, base_url: str, timeout: float) -> None:
            self.base_url = base_url
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(
            self,
            path: str,
            json: dict[str, object],
            headers: dict[str, str],
        ) -> DummyResponse:
            _ = path, json, headers
            call_count["value"] += 1
            if call_count["value"] == 1:
                raise httpx.ConnectError("temporary failure")
            return DummyResponse()

    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)

    response = anyio.run(
        lambda: post_json_model(
            service="chat-service",
            base_url="http://chat-service:8002",
            path="/v1/chat",
            payload=ChatRequest(message="hello"),
            headers={"x-request-id": "req-001"},
            timeout=10.0,
            retry_count=1,
            response_model=ChatResponse,
        )
    )

    assert response.service == "chat-service"
    assert call_count["value"] == 2


def test_post_json_model_raises_upstream_error_after_retries(monkeypatch) -> None:
    class DummyAsyncClient:
        def __init__(self, *, base_url: str, timeout: float) -> None:
            self.base_url = base_url
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(
            self,
            path: str,
            json: dict[str, object],
            headers: dict[str, str],
        ):
            _ = path, json, headers
            raise httpx.ConnectError("still failing")

    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)

    try:
        anyio.run(
            lambda: post_json_model(
                service="chat-service",
                base_url="http://chat-service:8002",
                path="/v1/chat",
                payload=ChatRequest(message="hello"),
                headers={"x-request-id": "req-001"},
                timeout=10.0,
                retry_count=1,
                response_model=ChatResponse,
            )
        )
        msg = "expected UpstreamServiceError"
        raise AssertionError(msg)
    except UpstreamServiceError as exc:
        assert exc.details["service"] == "chat-service"
        assert exc.details["attempts"] == 2


def test_post_json_model_omits_none_payload_fields(monkeypatch) -> None:
    captured_payload: dict[str, object] = {}

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"service": "rag-service", "query": "hello", "contexts": []}

    class DummyAsyncClient:
        def __init__(self, *, base_url: str, timeout: float) -> None:
            self.base_url = base_url
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(
            self,
            path: str,
            json: dict[str, object],
            headers: dict[str, str],
        ) -> DummyResponse:
            _ = path, headers
            captured_payload.update(json)
            return DummyResponse()

    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)

    response = anyio.run(
        lambda: post_json_model(
            service="rag-service",
            base_url="http://rag-service:8003",
            path="/v1/retrieve",
            payload=RetrieveRequest(query="hello", tenant_id="tenant-a"),
            headers={"x-request-id": "req-001"},
            timeout=10.0,
            retry_count=0,
            response_model=RetrieveResponse,
        )
    )

    assert response.service == "rag-service"
    assert captured_payload == {"query": "hello", "tenant_id": "tenant-a"}
