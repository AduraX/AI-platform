from python_common import AppSettings
from python_common.schemas import RequestContext, VectorIndexChunk, VectorIndexRequest

from ingestion_service.chunking import split_text
from ingestion_service.clients import create_embedding, index_chunks


async def index_document_text(
    *,
    settings: AppSettings,
    document_id: str,
    text: str,
    context: RequestContext,
) -> int:
    chunks: list[VectorIndexChunk] = []
    for index, content in enumerate(split_text(text), start=1):
        embedding = await create_embedding(settings=settings, text=content, context=context)
        chunk_id = f"{document_id}-chunk-{index:04d}"
        chunks.append(
            VectorIndexChunk(
                chunk_id=chunk_id,
                content=content,
                source=f"document://{document_id}/{chunk_id}",
                embedding=embedding.embedding,
            )
        )

    if not chunks:
        return 0

    response = await index_chunks(
        settings=settings,
        payload=VectorIndexRequest(document_id=document_id, chunks=chunks),
        context=context,
    )
    return response.indexed_count
