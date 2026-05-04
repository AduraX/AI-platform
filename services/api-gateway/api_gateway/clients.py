from python_common import AppSettings
from python_common.schemas import ChatRequest, ChatResponse, RequestContext
from python_common.web import post_json_model, request_context_to_headers


async def send_chat_message(
    *,
    settings: AppSettings,
    payload: ChatRequest,
    context: RequestContext,
) -> ChatResponse:
    response = await post_json_model(
        service="chat-service",
        base_url=settings.chat_service_base_url,
        path="/v1/chat",
        payload=payload,
        headers=request_context_to_headers(context),
        timeout=settings.request_timeout_seconds,
        retry_count=settings.upstream_retry_count,
        response_model=ChatResponse,
    )
    return ChatResponse.model_validate(response.model_dump())
