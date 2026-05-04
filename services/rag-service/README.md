# RAG Service

Retrieval orchestration against vector search and metadata filters.

The service selects a vector backend with `VECTOR_STORE_BACKEND=qdrant|milvus`.
It expects retrieval requests to include a `query_embedding` vector and uses
`RETRIEVAL_TOP_K` when the request does not provide `top_k`.

Current endpoints:

- `POST /v1/index`: stores embedded document chunks in the selected vector backend
- `POST /v1/retrieve`: searches tenant-scoped chunks with a query embedding

Local defaults target Qdrant. Milvus can be selected by setting
`VECTOR_STORE_BACKEND=milvus` and configuring `MILVUS_HOST`/`MILVUS_PORT`.

Local run:

```bash
cd services/rag-service && uv run uvicorn rag_service.main:app --reload --port 8003
```
