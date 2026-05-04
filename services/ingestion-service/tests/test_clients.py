import anyio
import httpx
from ingestion_service.clients import create_embedding, index_chunks
from python_common import AppSettings
from python_common.schemas import RequestContext, VectorIndexChunk, VectorIndexRequest


def test_create_embedding_forwards_identity_headers(monkeypatch) -> None:
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
            assert json == {"input": "policy text", "model": "embed-test"}
            assert headers["x-tenant-id"] == "tenant-a"
            assert headers["x-user-id"] == "user-123"
            assert headers["x-request-id"] == "req-001"
            return DummyResponse()

    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)

    response = anyio.run(
        lambda: create_embedding(
            settings=AppSettings(
                service_name="ingestion-service",
                model_router_base_url="http://model-router:8006",
                embedding_model="embed-test",
            ),
            text="policy text",
            context=RequestContext(
                tenant_id="tenant-a",
                user_id="user-123",
                request_id="req-001",
            ),
        )
    )

    assert response.embedding == [0.1, 0.2]


def test_index_chunks_forwards_identity_headers(monkeypatch) -> None:
    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "service": "rag-service",
                "document_id": "doc-1",
                "indexed_count": 1,
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
            assert path == "/v1/index"
            assert json["document_id"] == "doc-1"
            assert json["chunks"][0]["chunk_id"] == "chunk-1"
            assert json["chunks"][0]["embedding"] == [0.1, 0.2]
            assert headers["x-tenant-id"] == "tenant-a"
            assert headers["x-user-id"] == "user-123"
            assert headers["x-request-id"] == "req-001"
            return DummyResponse()

    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)

    response = anyio.run(
        lambda: index_chunks(
            settings=AppSettings(
                service_name="ingestion-service",
                rag_service_base_url="http://rag-service:8003",
            ),
            payload=VectorIndexRequest(
                document_id="doc-1",
                chunks=[
                    VectorIndexChunk(
                        chunk_id="chunk-1",
                        content="policy text",
                        source="document://doc-1/chunk-1",
                        embedding=[0.1, 0.2],
                    )
                ],
            ),
            context=RequestContext(
                tenant_id="tenant-a",
                user_id="user-123",
                request_id="req-001",
            ),
        )
    )

    assert response.indexed_count == 1
