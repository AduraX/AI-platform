# Chat Service

Conversation orchestration, streaming responses, and RAG coordination.

The chat path requests a query embedding from `model-router` before calling `rag-service`, then composes the response from retrieved contexts.

Local run:

```bash
cd services/chat-service && uv run uvicorn chat_service.main:app --reload --port 8002
```
