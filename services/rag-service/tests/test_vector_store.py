import pytest
from python_common import AppSettings, PlatformError
from rag_service.vector_store import MilvusVectorStore, QdrantVectorStore, create_vector_store


class FakeQdrantPoint:
    id = "point-1"
    score = 0.87

    def __init__(self) -> None:
        self.payload = {
            "chunk_id": "chunk-1",
            "content": "Qdrant context",
            "source": "doc://qdrant/chunk-1",
        }


class FakeQdrantResponse:
    def __init__(self) -> None:
        self.points = [FakeQdrantPoint()]


class FakeQdrantClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def query_points(self, **kwargs):
        self.calls.append(kwargs)
        return FakeQdrantResponse()

    def upsert(self, **kwargs):
        self.calls.append(kwargs)


class FakeMilvusClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def search(self, **kwargs):
        self.calls.append(kwargs)
        return [
            [
                {
                    "id": "point-1",
                    "distance": 0.82,
                    "entity": {
                        "chunk_id": "chunk-1",
                        "content": "Milvus context",
                        "source": "doc://milvus/chunk-1",
                    },
                }
            ]
        ]

    def insert(self, **kwargs):
        self.calls.append(kwargs)


def test_create_vector_store_defaults_to_qdrant() -> None:
    store = create_vector_store(
        AppSettings(
            service_name="rag-service",
            qdrant_host="qdrant",
            qdrant_port=6333,
        )
    )

    assert isinstance(store, QdrantVectorStore)
    assert store.host == "qdrant"
    assert store.port == 6333
    assert store.collection_name == "document_chunks"


def test_create_vector_store_accepts_milvus() -> None:
    store = create_vector_store(
        AppSettings(
            service_name="rag-service",
            vector_store_backend="milvus",
            milvus_host="milvus",
            milvus_port=19530,
        )
    )

    assert isinstance(store, MilvusVectorStore)
    assert store.host == "milvus"
    assert store.port == 19530
    assert store.collection_name == "document_chunks"


def test_qdrant_vector_store_queries_client() -> None:
    client = FakeQdrantClient()
    store = QdrantVectorStore(
        host="qdrant",
        port=6333,
        collection_name="chunks",
        content_payload_key="content",
        source_payload_key="source",
        tenant_payload_key="tenant_id",
        client=client,
    )

    contexts = store.retrieve(
        query="policy",
        tenant_id="tenant-a",
        query_embedding=[0.1, 0.2],
        top_k=3,
    )

    assert client.calls[0]["collection_name"] == "chunks"
    assert client.calls[0]["query"] == [0.1, 0.2]
    assert client.calls[0]["limit"] == 3
    assert contexts[0].content == "Qdrant context"
    assert contexts[0].source == "doc://qdrant/chunk-1"


def test_qdrant_vector_store_indexes_chunks() -> None:
    from python_common.schemas import VectorIndexChunk

    client = FakeQdrantClient()
    store = QdrantVectorStore(
        host="qdrant",
        port=6333,
        collection_name="chunks",
        content_payload_key="content",
        source_payload_key="source",
        tenant_payload_key="tenant_id",
        client=client,
    )

    indexed_count = store.index(
        document_id="doc-1",
        tenant_id="tenant-a",
        chunks=[
            VectorIndexChunk(
                chunk_id="chunk-1",
                content="Policy text",
                source="doc://doc-1/chunk-1",
                embedding=[0.1, 0.2],
            )
        ],
    )

    point = client.calls[0]["points"][0]
    assert indexed_count == 1
    assert client.calls[0]["collection_name"] == "chunks"
    assert point.id == "chunk-1"
    assert point.vector == [0.1, 0.2]
    assert point.payload["tenant_id"] == "tenant-a"
    assert point.payload["document_id"] == "doc-1"
    assert point.payload["content"] == "Policy text"


def test_milvus_vector_store_queries_client() -> None:
    client = FakeMilvusClient()
    store = MilvusVectorStore(
        host="milvus",
        port=19530,
        collection_name="chunks",
        embedding_field="embedding",
        content_payload_key="content",
        source_payload_key="source",
        tenant_payload_key="tenant_id",
        client=client,
    )

    contexts = store.retrieve(
        query="policy",
        tenant_id="tenant-a",
        query_embedding=[0.1, 0.2],
        top_k=3,
    )

    assert client.calls[0]["collection_name"] == "chunks"
    assert client.calls[0]["data"] == [[0.1, 0.2]]
    assert client.calls[0]["anns_field"] == "embedding"
    assert client.calls[0]["filter"] == 'tenant_id == "tenant-a"'
    assert client.calls[0]["limit"] == 3
    assert contexts[0].content == "Milvus context"
    assert contexts[0].source == "doc://milvus/chunk-1"


def test_milvus_vector_store_indexes_chunks() -> None:
    from python_common.schemas import VectorIndexChunk

    client = FakeMilvusClient()
    store = MilvusVectorStore(
        host="milvus",
        port=19530,
        collection_name="chunks",
        embedding_field="embedding",
        content_payload_key="content",
        source_payload_key="source",
        tenant_payload_key="tenant_id",
        client=client,
    )

    indexed_count = store.index(
        document_id="doc-1",
        tenant_id="tenant-a",
        chunks=[
            VectorIndexChunk(
                chunk_id="chunk-1",
                content="Policy text",
                source="doc://doc-1/chunk-1",
                embedding=[0.1, 0.2],
            )
        ],
    )

    row = client.calls[0]["data"][0]
    assert indexed_count == 1
    assert client.calls[0]["collection_name"] == "chunks"
    assert row["chunk_id"] == "chunk-1"
    assert row["embedding"] == [0.1, 0.2]
    assert row["tenant_id"] == "tenant-a"
    assert row["document_id"] == "doc-1"
    assert row["content"] == "Policy text"


def test_vector_store_requires_query_embedding() -> None:
    store = QdrantVectorStore(
        host="qdrant",
        port=6333,
        collection_name="chunks",
        content_payload_key="content",
        source_payload_key="source",
        tenant_payload_key="tenant_id",
        client=FakeQdrantClient(),
    )

    with pytest.raises(PlatformError) as exc_info:
        store.retrieve(query="policy", tenant_id="tenant-a", query_embedding=None, top_k=3)

    assert exc_info.value.code == "missing_query_embedding"
