"""Tests for streaming chat endpoint."""
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from python_common.schemas import EmbeddingResponse, RetrievalContext, RetrieveResponse


def test_stream_endpoint_returns_event_stream():
    """Test that the streaming endpoint returns SSE content type."""
    from chat_service.main import app

    with (
        patch(
            "chat_service.routes.create_query_embedding",
            new_callable=AsyncMock,
        ) as mock_embed,
        patch(
            "chat_service.routes.fetch_retrieval_context",
            new_callable=AsyncMock,
        ) as mock_retrieve,
    ):

        mock_embed.return_value = EmbeddingResponse(
            service="model-router", model="test", embedding=[0.1, 0.2]
        )
        mock_retrieve.return_value = RetrieveResponse(
            service="rag-service",
            query="test",
            contexts=[
                RetrievalContext(
                    chunk_id="c1", content="test content", score=0.9, source="test://doc"
                )
            ],
        )

        client = TestClient(app)
        response = client.post(
            "/v1/chat/stream",
            json={"message": "test query", "stream": True},
            headers={"x-tenant-id": "test-tenant"},
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
