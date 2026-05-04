from chat_service.orchestration import compose_chat_reply
from python_common.schemas import RetrievalContext, RetrieveResponse


def test_compose_chat_reply_includes_sources() -> None:
    retrieval = RetrieveResponse(
        service="rag-service",
        query="hello",
        contexts=[
            RetrievalContext(
                chunk_id="chunk-1",
                content="Reference material",
                score=0.91,
                source="tenant:default/knowledge-base",
            )
        ],
    )

    response = compose_chat_reply(message="hello", retrieval=retrieval)

    assert response.service == "chat-service"
    assert response.sources == ["tenant:default/knowledge-base"]
    assert "grounded with 1 context chunk" in response.reply
