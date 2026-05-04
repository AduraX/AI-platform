from typing import Any, Protocol

from python_common import AppSettings, PlatformError
from python_common.schemas import RetrievalContext, VectorIndexChunk


class VectorStore(Protocol):
    backend_name: str

    def index(self, *, document_id: str, tenant_id: str, chunks: list[VectorIndexChunk]) -> int:
        """Store tenant-scoped document chunks for retrieval."""

    def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        query_embedding: list[float] | None,
        top_k: int,
    ) -> list[RetrievalContext]:
        """Return tenant-scoped retrieval contexts for a query."""


def _require_query_embedding(query_embedding: list[float] | None) -> list[float]:
    if query_embedding:
        return query_embedding

    raise PlatformError(
        code="missing_query_embedding",
        message="Retrieval requires a query embedding.",
        status_code=400,
    )


def _payload_value(payload: dict[str, Any], key: str, default: str = "") -> str:
    value = payload.get(key, default)
    return str(value) if value is not None else default


class QdrantVectorStore:
    backend_name = "qdrant"

    def __init__(
        self,
        *,
        host: str,
        port: int,
        collection_name: str,
        content_payload_key: str,
        source_payload_key: str,
        tenant_payload_key: str,
        client: Any | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.content_payload_key = content_payload_key
        self.source_payload_key = source_payload_key
        self.tenant_payload_key = tenant_payload_key
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(host=self.host, port=self.port)
        return self._client

    def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        query_embedding: list[float] | None,
        top_k: int,
    ) -> list[RetrievalContext]:
        embedding = _require_query_embedding(query_embedding)

        from qdrant_client.models import FieldCondition, Filter, MatchValue

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=embedding,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key=self.tenant_payload_key,
                        match=MatchValue(value=tenant_id),
                    )
                ]
            ),
            limit=top_k,
            with_payload=True,
        )

        contexts: list[RetrievalContext] = []
        for point in response.points:
            payload = point.payload or {}
            contexts.append(
                RetrievalContext(
                    chunk_id=_payload_value(payload, "chunk_id", str(point.id)),
                    content=_payload_value(payload, self.content_payload_key),
                    score=float(point.score or 0.0),
                    source=_payload_value(
                        payload,
                        self.source_payload_key,
                        f"qdrant://{self.host}:{self.port}/{self.collection_name}/{point.id}",
                    ),
                )
            )

        return contexts

    def index(self, *, document_id: str, tenant_id: str, chunks: list[VectorIndexChunk]) -> int:
        from qdrant_client.models import PointStruct

        points = [
            PointStruct(
                id=chunk.chunk_id,
                vector=chunk.embedding,
                payload={
                    "chunk_id": chunk.chunk_id,
                    "document_id": document_id,
                    self.content_payload_key: chunk.content,
                    self.source_payload_key: chunk.source,
                    self.tenant_payload_key: tenant_id,
                },
            )
            for chunk in chunks
        ]
        self.client.upsert(collection_name=self.collection_name, points=points)
        return len(points)


class MilvusVectorStore:
    backend_name = "milvus"

    def __init__(
        self,
        *,
        host: str,
        port: int,
        collection_name: str,
        embedding_field: str,
        content_payload_key: str,
        source_payload_key: str,
        tenant_payload_key: str,
        client: Any | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.embedding_field = embedding_field
        self.content_payload_key = content_payload_key
        self.source_payload_key = source_payload_key
        self.tenant_payload_key = tenant_payload_key
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            from pymilvus import MilvusClient

            self._client = MilvusClient(uri=f"http://{self.host}:{self.port}")
        return self._client

    def retrieve(
        self,
        *,
        query: str,
        tenant_id: str,
        query_embedding: list[float] | None,
        top_k: int,
    ) -> list[RetrievalContext]:
        embedding = _require_query_embedding(query_embedding)

        results = self.client.search(
            collection_name=self.collection_name,
            data=[embedding],
            anns_field=self.embedding_field,
            filter=f'{self.tenant_payload_key} == "{tenant_id}"',
            limit=top_k,
            output_fields=[
                "chunk_id",
                self.content_payload_key,
                self.source_payload_key,
            ],
        )

        contexts: list[RetrievalContext] = []
        for hit in results[0] if results else []:
            entity = hit.get("entity", {})
            hit_id = hit.get("id", entity.get("chunk_id", "unknown"))
            contexts.append(
                RetrievalContext(
                    chunk_id=_payload_value(entity, "chunk_id", str(hit_id)),
                    content=_payload_value(entity, self.content_payload_key),
                    score=float(hit.get("distance", hit.get("score", 0.0)) or 0.0),
                    source=_payload_value(
                        entity,
                        self.source_payload_key,
                        f"milvus://{self.host}:{self.port}/{self.collection_name}/{hit_id}",
                    ),
                )
            )

        return contexts

    def index(self, *, document_id: str, tenant_id: str, chunks: list[VectorIndexChunk]) -> int:
        rows = [
            {
                "chunk_id": chunk.chunk_id,
                "document_id": document_id,
                self.embedding_field: chunk.embedding,
                self.content_payload_key: chunk.content,
                self.source_payload_key: chunk.source,
                self.tenant_payload_key: tenant_id,
            }
            for chunk in chunks
        ]
        self.client.insert(collection_name=self.collection_name, data=rows)
        return len(rows)


def _vector_store_kwargs(settings: AppSettings) -> dict[str, str]:
    return {
        "collection_name": settings.vector_collection_name,
        "content_payload_key": settings.vector_content_payload_key,
        "source_payload_key": settings.vector_source_payload_key,
        "tenant_payload_key": settings.vector_tenant_payload_key,
    }


def create_vector_store(settings: AppSettings) -> VectorStore:
    common_kwargs = _vector_store_kwargs(settings)
    if settings.vector_store_backend == "milvus":
        return MilvusVectorStore(
            host=settings.milvus_host,
            port=settings.milvus_port,
            embedding_field=settings.vector_embedding_field,
            **common_kwargs,
        )

    return QdrantVectorStore(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        **common_kwargs,
    )
