from python_common import AppSettings
from python_common.schemas import (
    EmbeddingRequest,
    EmbeddingResponse,
    RequestContext,
    VectorIndexRequest,
    VectorIndexResponse,
)
from python_common.web import post_json_model, request_context_to_headers


async def create_embedding(
    *,
    settings: AppSettings,
    text: str,
    context: RequestContext,
) -> EmbeddingResponse:
    response = await post_json_model(
        service="model-router",
        base_url=settings.model_router_base_url,
        path="/v1/embeddings",
        payload=EmbeddingRequest(input=text, model=settings.embedding_model),
        headers=request_context_to_headers(context),
        timeout=settings.request_timeout_seconds,
        retry_count=settings.upstream_retry_count,
        response_model=EmbeddingResponse,
    )
    return EmbeddingResponse.model_validate(response.model_dump())


async def index_chunks(
    *,
    settings: AppSettings,
    payload: VectorIndexRequest,
    context: RequestContext,
) -> VectorIndexResponse:
    response = await post_json_model(
        service="rag-service",
        base_url=settings.rag_service_base_url,
        path="/v1/index",
        payload=payload,
        headers=request_context_to_headers(context),
        timeout=settings.request_timeout_seconds,
        retry_count=settings.upstream_retry_count,
        response_model=VectorIndexResponse,
    )
    return VectorIndexResponse.model_validate(response.model_dump())
