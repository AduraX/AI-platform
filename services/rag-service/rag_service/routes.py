from fastapi import APIRouter, Request
from python_common.schemas import (
    RetrieveRequest,
    RetrieveResponse,
    VectorIndexRequest,
    VectorIndexResponse,
)
from python_common.web import request_context_from_headers

from rag_service.vector_store import VectorStore


def create_retrieval_router(vector_store: VectorStore, *, default_top_k: int) -> APIRouter:
    router = APIRouter(tags=["retrieval"])

    @router.post("/v1/retrieve", response_model=RetrieveResponse)
    def retrieve(request: Request, payload: RetrieveRequest) -> RetrieveResponse:
        context = request_context_from_headers(request)
        return RetrieveResponse(
            service="rag-service",
            query=payload.query,
            contexts=vector_store.retrieve(
                query=payload.query,
                tenant_id=context.tenant_id,
                query_embedding=payload.query_embedding,
                top_k=payload.top_k or default_top_k,
            ),
        )

    @router.post("/v1/index", response_model=VectorIndexResponse)
    def index(request: Request, payload: VectorIndexRequest) -> VectorIndexResponse:
        context = request_context_from_headers(request)
        indexed_count = vector_store.index(
            document_id=payload.document_id,
            tenant_id=context.tenant_id,
            chunks=payload.chunks,
        )
        return VectorIndexResponse(
            service="rag-service",
            document_id=payload.document_id,
            indexed_count=indexed_count,
        )

    return router
