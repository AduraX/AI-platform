import anyio
from chat_service.routes import build_router
from python_common import AppSettings
from python_common.schemas import ChatRequest, EmbeddingResponse, RetrieveResponse
from starlette.requests import Request


def test_chat_route_embeds_before_retrieval(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    async def fake_create_query_embedding(**kwargs) -> EmbeddingResponse:
        calls.append(("embedding", kwargs["text"]))
        return EmbeddingResponse(
            service="model-router",
            model="embed-test",
            embedding=[0.1, 0.2],
        )

    async def fake_fetch_retrieval_context(**kwargs) -> RetrieveResponse:
        payload = kwargs["payload"]
        calls.append(("retrieval_embedding", payload.query_embedding))
        return RetrieveResponse(service="rag-service", query=payload.query, contexts=[])

    monkeypatch.setattr("chat_service.routes.create_query_embedding", fake_create_query_embedding)
    monkeypatch.setattr("chat_service.routes.fetch_retrieval_context", fake_fetch_retrieval_context)

    router = build_router(AppSettings(service_name="chat-service"))
    endpoint = next(route.endpoint for route in router.routes if route.path == "/v1/chat")
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat",
            "headers": [(b"x-tenant-id", b"tenant-a")],
        }
    )

    response = anyio.run(lambda: endpoint(request=request, payload=ChatRequest(message="hello")))

    assert calls == [("embedding", "hello"), ("retrieval_embedding", [0.1, 0.2])]
    assert response.service == "chat-service"
    assert "no retrieval context found" in response.reply
