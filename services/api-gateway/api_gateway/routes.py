import httpx
from fastapi import APIRouter, Request
from python_common import AppSettings
from python_common.schemas import ChatRequest, ChatResponse
from python_common.web import request_context_from_headers, request_context_to_headers
from starlette.responses import StreamingResponse

from api_gateway.clients import send_chat_message


def build_router(settings: AppSettings) -> APIRouter:
    router = APIRouter(tags=["gateway"])

    @router.post("/v1/chat", response_model=ChatResponse)
    async def chat(request: Request, payload: ChatRequest) -> ChatResponse:
        context = request_context_from_headers(request)
        return await send_chat_message(settings=settings, payload=payload, context=context)

    @router.post("/v1/chat/stream")
    async def chat_stream(request: Request, payload: ChatRequest):
        context = request_context_from_headers(request)
        headers = {**request_context_to_headers(context), "accept": "text/event-stream"}

        async def proxy_stream():
            async with httpx.AsyncClient(
                base_url=settings.chat_service_base_url, timeout=60.0
            ) as client, client.stream(
                "POST",
                "/v1/chat/stream",
                json=payload.model_dump(),
                headers=headers,
            ) as response:
                async for chunk in response.aiter_bytes():
                    yield chunk

        return StreamingResponse(proxy_stream(), media_type="text/event-stream")

    return router
