# Model Router

Unified inference boundary for Ollama, vLLM, and hosted model providers.

Current endpoints:

- `POST /v1/generate`
- `POST /v1/embeddings`

The embedding endpoint is provider-backed. By default it calls Ollama's `/api/embed` endpoint with `EMBEDDING_MODEL=embeddinggemma`. Set `EMBEDDING_PROVIDER=deterministic` only when an offline deterministic vector is needed for local tests or contract exercises.

For local Ollama embeddings:

```bash
ollama pull embeddinggemma
```

Local run:

```bash
cd services/model-router && uv run uvicorn model_router.main:app --reload --port 8006
```
