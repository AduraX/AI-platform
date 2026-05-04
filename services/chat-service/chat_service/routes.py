import asyncio
import json

from fastapi import APIRouter, Request
from python_common import AppSettings
from python_common.schemas import ChatRequest, ChatResponse, RetrieveRequest
from python_common.schemas.chat import ChatStreamRequest
from python_common.web import request_context_from_headers
from sse_starlette.sse import EventSourceResponse

from chat_service.clients import create_query_embedding, fetch_retrieval_context
from chat_service.orchestration import compose_chat_reply


def build_router(settings: AppSettings) -> APIRouter:
    router = APIRouter(tags=["chat"])

    @router.post("/v1/chat", response_model=ChatResponse)
    async def chat(request: Request, payload: ChatRequest) -> ChatResponse:
        context = request_context_from_headers(request)
        embedding = await create_query_embedding(
            settings=settings,
            text=payload.message,
            context=context,
        )
        retrieval = await fetch_retrieval_context(
            settings=settings,
            payload=RetrieveRequest(
                query=payload.message,
                tenant_id=context.tenant_id,
                query_embedding=embedding.embedding,
            ),
            context=context,
        )
        return compose_chat_reply(message=payload.message, retrieval=retrieval)

    @router.post("/v1/chat/stream")
    async def chat_stream(request: Request, payload: ChatStreamRequest):
        context = request_context_from_headers(request)

        async def event_generator():
            try:
                # Step 1: Emit status
                yield {"event": "status", "data": json.dumps({"step": "embedding"})}

                embedding = await create_query_embedding(
                    settings=settings,
                    text=payload.message,
                    context=context,
                )

                yield {"event": "status", "data": json.dumps({"step": "retrieving"})}

                retrieval = await fetch_retrieval_context(
                    settings=settings,
                    payload=RetrieveRequest(
                        query=payload.message,
                        tenant_id=context.tenant_id,
                        query_embedding=embedding.embedding,
                    ),
                    context=context,
                )

                # Step 2: Emit sources
                for ctx in retrieval.contexts:
                    yield {
                        "event": "source",
                        "data": json.dumps({
                            "chunk_id": ctx.chunk_id,
                            "content": ctx.content,
                            "score": ctx.score,
                            "source": ctx.source,
                        }),
                    }

                # Step 3: Emit reply tokens (simulate token-by-token streaming)
                reply = compose_chat_reply(message=payload.message, retrieval=retrieval)
                words = reply.reply.split()
                for i, word in enumerate(words):
                    token = word + (" " if i < len(words) - 1 else "")
                    yield {"event": "token", "data": token}
                    await asyncio.sleep(0.02)  # Simulate generation latency

                # Step 4: Done
                yield {
                    "event": "done",
                    "data": json.dumps({
                        "sources": reply.sources,
                        "context_count": len(retrieval.contexts),
                    }),
                }
            except Exception as e:
                yield {"event": "error", "data": json.dumps({"message": str(e)})}

        return EventSourceResponse(event_generator())

    return router
