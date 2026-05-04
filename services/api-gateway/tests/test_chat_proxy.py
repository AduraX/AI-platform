import anyio
import httpx
from api_gateway.clients import send_chat_message
from python_common import AppSettings
from python_common.schemas import ChatRequest, RequestContext


def test_send_chat_message_returns_chat_response(monkeypatch) -> None:
    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"service": "chat-service", "reply": "accepted: hello"}

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
            json: dict[str, str],
            headers: dict[str, str],
        ) -> DummyResponse:
            assert path == "/v1/chat"
            assert json == {"message": "hello"}
            assert headers["x-tenant-id"] == "tenant-a"
            assert headers["x-user-id"] == "user-123"
            assert headers["x-roles"] == "admin,analyst"
            assert headers["x-request-id"] == "req-001"
            return DummyResponse()

    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)

    settings = AppSettings(
        service_name="api-gateway",
        chat_service_base_url="http://chat-service:8002",
    )

    response = anyio.run(
        lambda: send_chat_message(
            settings=settings,
            payload=ChatRequest(message="hello"),
            context=RequestContext(
                tenant_id="tenant-a",
                user_id="user-123",
                roles=["admin", "analyst"],
                request_id="req-001",
            ),
        )
    )

    assert response.service == "chat-service"
    assert response.reply == "accepted: hello"
    assert response.sources == []
