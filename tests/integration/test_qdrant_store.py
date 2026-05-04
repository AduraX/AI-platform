"""Integration tests for Qdrant vector store.

Requires: docker compose up -d qdrant
Run with: uv run pytest -m integration tests/integration/test_qdrant_store.py
"""
import logging

import pytest
from python_common.schemas import VectorIndexChunk

pytestmark = pytest.mark.integration

COLLECTION_NAME = "integration_test_chunks"


@pytest.fixture
def qdrant_store():
    from rag_service.vector_store import QdrantVectorStore
    store = QdrantVectorStore(host="localhost", port=6333)
    # Override collection name for test isolation
    store.collection_name = COLLECTION_NAME
    yield store
    # Cleanup: delete test collection
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(host="localhost", port=6333)
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        logging.getLogger(__name__).debug("Collection cleanup skipped")


def test_index_and_retrieve(qdrant_store):
    # Index some chunks
    chunks = [
        VectorIndexChunk(
            chunk_id="q-chunk-001",
            content="Enterprise refund policy allows full refund within 30 days.",
            source="doc://policy/chunk-1",
            embedding=[0.1] * 64,
        ),
        VectorIndexChunk(
            chunk_id="q-chunk-002",
            content="Employees get 20 days of paid time off per year.",
            source="doc://handbook/chunk-1",
            embedding=[0.9] * 64,
        ),
    ]

    indexed = qdrant_store.index(
        document_id="q-doc-001",
        tenant_id="test-tenant",
        chunks=chunks,
    )
    assert indexed == 2

    # Retrieve with matching embedding
    results = qdrant_store.retrieve(
        query="refund policy",
        tenant_id="test-tenant",
        query_embedding=[0.1] * 64,
        top_k=5,
    )
    assert len(results) > 0
    assert any("refund" in r.content.lower() for r in results)


def test_tenant_isolation(qdrant_store):
    chunk_a = VectorIndexChunk(
        chunk_id="iso-a-001",
        content="Tenant A secret document.",
        source="doc://a/chunk-1",
        embedding=[0.5] * 64,
    )
    chunk_b = VectorIndexChunk(
        chunk_id="iso-b-001",
        content="Tenant B secret document.",
        source="doc://b/chunk-1",
        embedding=[0.5] * 64,
    )

    qdrant_store.index(document_id="doc-a", tenant_id="tenant-a", chunks=[chunk_a])
    qdrant_store.index(document_id="doc-b", tenant_id="tenant-b", chunks=[chunk_b])

    results_a = qdrant_store.retrieve(
        query="secret", tenant_id="tenant-a", query_embedding=[0.5] * 64, top_k=10
    )
    results_b = qdrant_store.retrieve(
        query="secret", tenant_id="tenant-b", query_embedding=[0.5] * 64, top_k=10
    )

    # Each tenant should only see their own data
    for r in results_a:
        assert "Tenant B" not in r.content
    for r in results_b:
        assert "Tenant A" not in r.content
