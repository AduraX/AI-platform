from fastapi import APIRouter
from python_common import AppSettings
from python_common.schemas import (
    EmbeddingRequest,
    EmbeddingResponse,
    GenerationAcceptedResponse,
    GenerationRequest,
)

from model_router.embeddings import create_embedding_provider


def build_router(settings: AppSettings) -> APIRouter:
    router = APIRouter(tags=["models"])
    embedding_provider = create_embedding_provider(settings)

    @router.post("/v1/generate", response_model=GenerationAcceptedResponse)
    def generate(payload: GenerationRequest) -> GenerationAcceptedResponse:
        return GenerationAcceptedResponse(
            service="model-router",
            model=payload.model or "default",
        )

    @router.post("/v1/embeddings", response_model=EmbeddingResponse)
    async def embeddings(payload: EmbeddingRequest) -> EmbeddingResponse:
        model = payload.model or settings.embedding_model
        return EmbeddingResponse(
            service="model-router",
            model=model,
            embedding=await embedding_provider.embed(text=payload.input, model=model),
        )

    return router
