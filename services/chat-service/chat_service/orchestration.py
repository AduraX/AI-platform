from python_common.schemas import ChatResponse, RetrieveResponse


def compose_chat_reply(*, message: str, retrieval: RetrieveResponse) -> ChatResponse:
    sources = [context.source for context in retrieval.contexts]

    if retrieval.contexts:
        reply = (
            f"accepted: {message} | grounded with {len(retrieval.contexts)} context "
            f"chunk(s) for query '{retrieval.query}'"
        )
    else:
        reply = f"accepted: {message} | no retrieval context found"

    return ChatResponse(
        service="chat-service",
        reply=reply,
        sources=sources,
    )
