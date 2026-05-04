from python_common.schemas import (
    RetrievalContext,
    RetrieveRequest,
    VectorIndexChunk,
    VectorIndexRequest,
)
from rag_service.routes import create_retrieval_router
from starlette.requests import Request


class FakeVectorStore:
    backend_name = "fake"

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        query_embedding: list[float] | None,
        top_k: int,
    ) -> list[RetrievalContext]:
        self.calls.append(
            {
                "query": query,
                "tenant_id": tenant_id,
                "query_embedding": query_embedding,
                "top_k": top_k,
            }
        )
        return [
            RetrievalContext(
                chunk_id="tenant-a-fake-chunk-001",
                content="Matched context",
                score=0.99,
                source="fake://tenant-a/knowledge-base",
            )
        ]

    def index(self, *, document_id: str, tenant_id: str, chunks: list[VectorIndexChunk]) -> int:
        self.calls.append(
            {
                "document_id": document_id,
                "tenant_id": tenant_id,
                "chunks": chunks,
            }
        )
        return len(chunks)


def test_retrieve_uses_injected_vector_store() -> None:
    vector_store = FakeVectorStore()
    router = create_retrieval_router(vector_store, default_top_k=5)
    endpoint = next(route.endpoint for route in router.routes if route.path == "/v1/retrieve")
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/retrieve",
            "headers": [(b"x-tenant-id", b"tenant-a")],
        }
    )

    response = endpoint(
        request=request,
        payload=RetrieveRequest(query="policy", query_embedding=[0.1, 0.2], top_k=3),
    )

    assert vector_store.calls == [
        {
            "query": "policy",
            "tenant_id": "tenant-a",
            "query_embedding": [0.1, 0.2],
            "top_k": 3,
        }
    ]
    assert response.model_dump() == {
        "service": "rag-service",
        "query": "policy",
        "contexts": [
            {
                "chunk_id": "tenant-a-fake-chunk-001",
                "content": "Matched context",
                "score": 0.99,
                "source": "fake://tenant-a/knowledge-base",
            }
        ],
        "pagination": None,
    }


def test_index_uses_injected_vector_store() -> None:
    vector_store = FakeVectorStore()
    router = create_retrieval_router(vector_store, default_top_k=5)
    endpoint = next(route.endpoint for route in router.routes if route.path == "/v1/index")
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/index",
            "headers": [(b"x-tenant-id", b"tenant-a")],
        }
    )
    chunk = VectorIndexChunk(
        chunk_id="chunk-1",
        content="Policy text",
        source="doc://doc-1/chunk-1",
        embedding=[0.1, 0.2],
    )

    response = endpoint(
        request=request,
        payload=VectorIndexRequest(document_id="doc-1", chunks=[chunk]),
    )

    assert vector_store.calls == [
        {
            "document_id": "doc-1",
            "tenant_id": "tenant-a",
            "chunks": [chunk],
        }
    ]
    assert response.model_dump() == {
        "service": "rag-service",
        "document_id": "doc-1",
        "indexed_count": 1,
    }
