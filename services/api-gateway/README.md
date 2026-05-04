# API Gateway

Public entrypoint for frontend traffic, auth-aware routing, and edge concerns.

Local run:

```bash
cd services/api-gateway && uv run uvicorn api_gateway.main:app --reload --port 8000
```
