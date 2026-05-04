import anyio
from ingestion_service.chunking import split_text
from ingestion_service.workflow import index_document_text
from python_common import AppSettings
from python_common.schemas import EmbeddingResponse, RequestContext, VectorIndexResponse


def test_split_text_chunks_by_word_count() -> None:
    text = " ".join(f"word-{index}" for index in range(125))

    chunks = split_text(text, max_words=120)

    assert len(chunks) == 2
    assert chunks[0].startswith("word-0 word-1")
    assert chunks[1] == "word-120 word-121 word-122 word-123 word-124"


def test_index_document_text_embeds_chunks_then_indexes(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    async def fake_create_embedding(**kwargs) -> EmbeddingResponse:
        calls.append(("embedding", kwargs["text"]))
        return EmbeddingResponse(
            service="model-router",
            model="embed-test",
            embedding=[0.1, 0.2],
        )

    async def fake_index_chunks(**kwargs) -> VectorIndexResponse:
        payload = kwargs["payload"]
        calls.append(("index", payload))
        return VectorIndexResponse(
            service="rag-service",
            document_id=payload.document_id,
            indexed_count=len(payload.chunks),
        )

    monkeypatch.setattr("ingestion_service.workflow.create_embedding", fake_create_embedding)
    monkeypatch.setattr("ingestion_service.workflow.index_chunks", fake_index_chunks)

    indexed_count = anyio.run(
        lambda: index_document_text(
            settings=AppSettings(service_name="ingestion-service"),
            document_id="doc-1",
            text="policy text",
            context=RequestContext(tenant_id="tenant-a", user_id="user-1"),
        )
    )

    assert indexed_count == 1
    assert calls[0] == ("embedding", "policy text")
    indexed_payload = calls[1][1]
    assert indexed_payload.document_id == "doc-1"
    assert indexed_payload.chunks[0].chunk_id == "doc-1-chunk-0001"
    assert indexed_payload.chunks[0].embedding == [0.1, 0.2]
    assert indexed_payload.chunks[0].source == "document://doc-1/doc-1-chunk-0001"
