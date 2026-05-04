import anyio
import httpx
from chat_service.clients import create_query_embedding, fetch_retrieval_context
from python_common import AppSettings
from python_common.schemas import RequestContext, RetrieveRequest


def test_fetch_retrieval_context_forwards_identity_headers(monkeypatch) -> None:
    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "service": "rag-service",
                "query": "hello",
                "contexts": [
                    {
                        "chunk_id": "tenant-a-chunk-001",
                        "content": "Reference material for 'hello'",
                        "score": 0.91,
                        "source": "tenant:tenant-a/knowledge-base",
                    }
                ],
            }

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
            assert path == "/v1/retrieve"
            assert json == {"query": "hello", "tenant_id": "tenant-a"}
            assert headers["x-tenant-id"] == "tenant-a"
            assert headers["x-user-id"] == "user-123"
            assert headers["x-roles"] == "admin"
            assert headers["x-request-id"] == "req-001"
            return DummyResponse()

    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)

    settings = AppSettings(service_name="chat-service", rag_service_base_url="http://rag-service:8003")

    response = anyio.run(
        lambda: fetch_retrieval_context(
            settings=settings,
            payload=RetrieveRequest(query="hello", tenant_id="tenant-a"),
            context=RequestContext(
                tenant_id="tenant-a",
                user_id="user-123",
                roles=["admin"],
                request_id="req-001",
            ),
        )
    )

    assert response.service == "rag-service"
    assert response.contexts[0].source == "tenant:tenant-a/knowledge-base"


def test_create_query_embedding_forwards_identity_headers(monkeypatch) -> None:
    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "service": "model-router",
                "model": "embed-test",
                "embedding": [0.1, 0.2],
            }

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
            assert path == "/v1/embeddings"
            assert json == {"input": "hello", "model": "embed-test"}
            assert headers["x-tenant-id"] == "tenant-a"
            assert headers["x-user-id"] == "user-123"
            assert headers["x-request-id"] == "req-001"
            return DummyResponse()

    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)

    settings = AppSettings(
        service_name="chat-service",
        model_router_base_url="http://model-router:8006",
        embedding_model="embed-test",
    )

    response = anyio.run(
        lambda: create_query_embedding(
            settings=settings,
            text="hello",
            context=RequestContext(
                tenant_id="tenant-a",
                user_id="user-123",
                roles=["admin"],
                request_id="req-001",
            ),
        )
    )

    assert response.service == "model-router"
    assert response.embedding == [0.1, 0.2]
