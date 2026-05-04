# Shared API Contracts

## Purpose

The platform now keeps cross-service request and response models in `shared/python-common` so contract definitions are versioned in one place and reused by every FastAPI service.

## Contract Modules

- `python_common.schemas.common`
  - `HealthResponse`
  - `AcceptedResponse`
- `python_common.schemas.chat`
  - `ChatRequest`
  - `ChatResponse`
- `python_common.schemas.auth`
  - `RequestContext`
- `python_common.schemas.documents`
  - `DocumentRequest`
  - `DocumentCreatedResponse`
  - `OcrRequest`
- `python_common.schemas.retrieval`
  - `RetrieveRequest`
  - `RetrievalContext`
  - `RetrieveResponse`
- `python_common.schemas.models`
  - `GenerationRequest`
  - `GenerationAcceptedResponse`
- `python_common.schemas.evaluation`
  - `EvalRequest`
  - `EvalCreatedResponse`

## Service Bootstrap

Common FastAPI initialization now lives in `python_common.web.app_factory`.

It currently standardizes:

- logging setup
- app creation
- `/health` route registration
- health payload shape across services
- platform error handler registration

## Shared Error Envelope

Platform-level application errors now return a shared payload:

```json
{
  "error": {
    "code": "upstream_service_error",
    "message": "chat-service is unavailable",
    "details": {
      "service": "chat-service"
    }
  }
}
```

## Current Route Ownership

- `api-gateway`: shared health route only
- `chat-service`: `/v1/chat`
- `rag-service`: `/v1/retrieve`
- `ingestion-service`: `/v1/documents`
- `ocr-service`: `/internal/ocr`
- `model-router`: `/v1/generate`
- `eval-service`: `/v1/evals`

## Next Extension Points

- add shared error envelopes
- add pagination and filtering primitives
- expose OpenAPI export per service from these shared contracts
- replace internal header-based identity propagation with validated auth claims
