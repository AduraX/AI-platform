# Building a Private Enterprise AI Platform from Scratch

## Part 1: Architecture, Services, and Local-First Design

*How we designed a self-hosted AI platform with FastAPI, Next.js, and Kubernetes — and why every decision optimized for "run it locally in five minutes, deploy to production without rewriting."*

---

There is no shortage of AI wrappers. What there is a shortage of is AI infrastructure you can actually own — that runs on your hardware, behind your firewall, with your auth, your data, and your compliance requirements.

That is the problem we set out to solve. Not another chatbot demo. A real platform — one that handles multi-tenant isolation, document ingestion pipelines, vector search, model routing, background job processing, and Kubernetes deployment. One that a team of engineers can fork, understand in an afternoon, and extend for their own use cases.

This is Part 1 of a two-part series. Here we will cover the architecture, the service design decisions, and the local development experience. In Part 2, we will go deep on RAG, embeddings, ingestion pipelines, production hardening, and Kubeflow integration.

---

### The Problem With Most AI Platform Tutorials

Most "build your own AI" tutorials fall into one of two traps.

The first trap is the single-file demo. A hundred lines of LangChain in a Jupyter notebook that calls OpenAI, dumps results to stdout, and calls it a platform. No auth. No multi-tenancy. No persistence. No tests. It works on the author's laptop and nowhere else.

The second trap is the enterprise overengineering. Fifty Kubernetes manifests, a service mesh, three message brokers, and a twelve-page architecture diagram — before a single user query has been answered. The team spends six months building infrastructure and never ships the product.

We wanted neither. We wanted something that boots locally with `docker compose up` and a handful of `uvicorn` commands, that has real service boundaries you can reason about, and that deploys to Kubernetes without a rewrite.

---

### Architecture Overview

The platform is a modular monorepo with eight services, a shared Python library, a Next.js frontend, and Kustomize-based Kubernetes deployment.

```
    +-------------------+
    |     Frontend      |
    |   Next.js :3000   |
    +---------+---------+
              |
    +---------v---------+
    |    API Gateway     |
    |       :8000        |
    +---------+---------+
              |
   +----------+----------+-----------------+
   |          |          |                 |
   v          v          v                 v
+------+  +-------+  +--------+     +---------+
| Chat |  | Ingest|  | Model  |     |  Eval   |
| Svc  |  |  Svc  |  | Router |     |  Svc    |
| :8002|  | :8004 |  | :8006  |     | :8007   |
+--+---+  +--+----+  +---+----+     +---------+
   |         |            |
   |    +----+----+       |
   |    |         |       |
   v    v         v       v
+------+---+  +---+----+ +--------+
| RAG Svc  |  | OCR Svc| | Ollama |
|  :8003   |  | :8005  | | /vLLM  |
+----+-----+  +---+----+ +--------+
     |            |
     v            v
+---------+  +---------+  +----------+  +---------+
| Qdrant/ |  | MinIO   |  | Postgres |  |  Redis  |
| Milvus  |  | (S3)    |  |          |  |         |
+---------+  +---------+  +----------+  +---------+
```

Here is the key insight: **every arrow in this diagram is an HTTP call with forwarded context headers.** There is no shared database between services. There is no message bus you have to understand before you can trace a request. When a user sends a chat message, you can follow the request from the API Gateway through the Chat Service, into the Model Router for embeddings, into the RAG Service for retrieval, and back — all with `curl` and a few log lines.

---

### Why These Services? Why This Split?

Each service exists because it has a distinct scaling profile and a distinct failure domain.

**API Gateway** (`api-gateway`, port 8000) is the only service exposed to the public network. It forwards requests, propagates authentication context, and adds the correlation headers (`x-tenant-id`, `x-user-id`, `x-roles`, `x-request-id`) that every downstream service reads. If the gateway goes down, nothing works. If the eval service goes down, chat still works.

**Chat Service** (`chat-service`, port 8002) is the orchestrator. It does not generate text or search vectors itself. It coordinates: ask the Model Router for an embedding, ask the RAG Service for relevant context, compose the final prompt, and return the response. This keeps the chat logic free of infrastructure coupling. You can swap vector databases without touching the chat code.

**RAG Service** (`rag-service`, port 8003) owns the vector store abstraction. It speaks to Qdrant or Milvus through a `VectorStore` protocol with two operations: `retrieve` and `index`. The backend is selected by a single environment variable (`VECTOR_STORE_BACKEND=qdrant`). Adding a third vector database means implementing one Python protocol — no changes to any other service.

```python
class VectorStore(Protocol):
    backend_name: str

    def retrieve(self, *, query: str, tenant_id: str,
                 query_embedding: list[float] | None,
                 top_k: int) -> list[RetrievalContext]: ...

    def index(self, *, document_id: str, tenant_id: str,
              chunks: list[VectorIndexChunk]) -> int: ...
```

**Ingestion Service** (`ingestion-service`, port 8004) is the most complex service and the one that most tutorials skip entirely. It handles document registration, text chunking, embedding coordination (through Model Router), vector indexing (through RAG Service), job tracking (in-memory or PostgreSQL), and queue management (in-memory or Redis). It supports synchronous processing for local development and background processing with a durable worker contract for production.

**Model Router** (`model-router`, port 8006) abstracts embedding and generation providers. The default embedding provider is Ollama for local development, with a deterministic fallback that requires no external model. Adding vLLM or a hosted API means implementing one more `EmbeddingProvider` — no changes to any calling service.

**OCR Service** and **Eval Service** are scaffolded boundaries — they have health checks, routes, and schemas, but the implementation is intentionally thin. They exist in the architecture because removing a service boundary later is much harder than filling one in.

---

### The Shared Library: Where Opinions Live

The `shared/python-common` package is where we enforce consistency across services. It contains:

- **Pydantic schemas** for every cross-service request and response
- **AppSettings** — a single `BaseSettings` class that every service uses for configuration
- **App factory** — `create_service_app()` wires up CORS, security headers, JWT validation, request context extraction, Prometheus metrics, structured logging, health checks, and error handling in one call
- **Service client helpers** — `post_json()` and `post_json_model()` for service-to-service HTTP with automatic header forwarding and retry
- **Error handling** — a `PlatformError` base class with structured error envelopes

Here is what a service's `main.py` looks like:

```python
from python_common import AppSettings
from python_common.web import create_service_app
from api_gateway.routes import build_router

settings = AppSettings(service_name="api-gateway")
app = create_service_app(title="API Gateway", version="0.1.0", settings=settings)
app.include_router(build_router(settings))
```

Four lines. Every service gets CORS, security headers, structured JSON logging, Prometheus metrics, health checks, JWT validation (when enabled), and consistent error handling — without writing any of it themselves.

---

### Multi-Tenancy Without a Multi-Tenancy Framework

Every request in the system carries a `RequestContext`:

```python
class RequestContext(BaseModel):
    tenant_id: str = Field(default="default")
    user_id: str = Field(default="anonymous")
    roles: list[str] = Field(default_factory=list)
    request_id: str = Field(default="unknown")
```

This context is extracted from HTTP headers by middleware in the app factory. When `AUTH_ENABLED=true`, the middleware validates the JWT from Keycloak and extracts claims (`email`, `tenant_id`, `realm_access.roles`) into the context — no service code needs to know about JWT validation.

The context flows through every service-to-service call:

```python
# In any service making an upstream call:
response = await post_json_model(
    client=http_client,
    url=f"{settings.rag_service_base_url}/v1/retrieve",
    payload=retrieve_request,
    response_model=RetrieveResponse,
    context=request.state.request_context,  # Headers forwarded automatically
)
```

The RAG Service uses `tenant_id` to filter vector store queries. The Ingestion Service stores it alongside job records. The pattern is simple: every request knows who is asking, and every data access respects it.

---

### Configuration: One Class, Zero Magic

All configuration lives in one `AppSettings` class backed by Pydantic Settings:

```python
class AppSettings(BaseSettings):
    service_name: str = "service"
    environment: str = "development"
    log_level: str = "INFO"

    vector_store_backend: Literal["qdrant", "milvus"] = "qdrant"
    embedding_provider: Literal["deterministic", "ollama"] = "ollama"
    ingestion_job_store_backend: Literal["memory", "postgres"] = "memory"
    ingestion_queue_backend: Literal["memory", "redis"] = "memory"

    auth_enabled: bool = False
    cors_allowed_origins: list[str] = ["http://localhost:3000"]

    # ... infrastructure endpoints, service URLs, etc.

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
```

Every setting has a sensible local default. You can boot the entire platform with `cp .env.example .env` and change nothing. When you deploy to Kubernetes, the same settings are injected via ConfigMap and Secret — same code, same class, different values.

The `Literal` types are important. If someone sets `VECTOR_STORE_BACKEND=pinecone`, Pydantic rejects it at startup with a clear validation error — not at runtime when the first query fails.

---

### The Local Development Experience

This is what getting started actually looks like:

```bash
git clone <repo> && cd AI-platform
cp .env.example .env
docker compose up -d                      # Postgres, Redis, Qdrant, MinIO
uv sync --all-packages --dev              # Install everything
cd apps/frontend && npm install && cd ..

# Option A: Real embeddings
ollama pull embeddinggemma

# Option B: No external model needed
echo "EMBEDDING_PROVIDER=deterministic" >> .env

uv run pytest --cov                       # 58 passed, 81% coverage
```

Five minutes. No Kubernetes. No Terraform. No cloud account.

Each backend service is a single `uvicorn` command:

```bash
uv run uvicorn api_gateway.main:app --reload --port 8000
```

The `--reload` flag means you edit a file, save it, and the change is live. The shared library is installed as an editable package, so changes to `python-common` are picked up immediately by every service.

This is not an accident. **The local experience was designed before the Kubernetes manifests.** If something is hard to run locally, it is hard to debug in production. Every infrastructure dependency (Postgres, Redis, Qdrant, MinIO) has an in-memory alternative for tests, and every external service call has a deterministic fallback.

---

### Observability From Day One

Every service ships with three observability primitives built into the app factory — no per-service configuration needed.

**Structured JSON logging** outputs one JSON object per log line:

```json
{
  "timestamp": "2026-04-29T12:00:00+00:00",
  "level": "INFO",
  "logger": "python_common.web.app_factory",
  "message": "request service=api-gateway method=POST path=/v1/chat status=200",
  "service": "api-gateway",
  "tenant_id": "acme-corp",
  "request_id": "abc-123",
  "duration_ms": 42.5
}
```

Every log line includes the service name, tenant, request ID, and duration. You can grep across services by `request_id` to trace a single user request end to end.

**Prometheus metrics** are exposed on `/metrics`:

```
api_gateway_http_requests_total{method="POST",path="/v1/chat",status="200"} 1423
api_gateway_http_request_duration_seconds_sum{method="POST",path="/v1/chat",status="200"} 12.847
```

**Health checks** at `/health` return structured status:

```json
{"service": "ingestion-service", "status": "ok", "environment": "production", "checks": {}}
```

The Kubernetes liveness, readiness, and startup probes point at these endpoints. If a service is unhealthy, Kubernetes restarts it. If it is not ready, traffic stops routing to it. No custom health check code in any service.

---

### What We Deliberately Left Out

Every architecture is defined as much by what it excludes as what it includes.

**No message broker.** Service-to-service calls are synchronous HTTP. This is a deliberate choice for a platform this size. A Kafka or RabbitMQ cluster adds operational complexity that is not justified until you have throughput that demands it. The ingestion queue abstraction uses Redis for durable job handoff — that is enough for thousands of documents per day.

**No ORM.** The PostgreSQL code uses raw `psycopg` with parameterized queries and connection pooling. An ORM adds a layer of abstraction that makes it harder to reason about what queries are actually running. For seven services with simple schemas, raw SQL is clearer.

**No LangChain.** The RAG pipeline is explicit: chunk text, embed chunks, index embeddings, retrieve by similarity. Each step is a function call you can read and debug. The abstraction is the `VectorStore` protocol and the `EmbeddingProvider` protocol — not a framework.

**No streaming (yet).** Chat responses are returned as complete JSON. Streaming is a natural next step, but it changes the middleware, error handling, and client contract. We chose to ship a working synchronous path first and add streaming as a targeted enhancement.

---

### What is Next

In Part 2, we will go deep on the pieces that make this platform production-real rather than demo-ready:

- The RAG pipeline: how retrieval, embeddings, and vector indexing actually work across Qdrant and Milvus
- The ingestion pipeline: chunking strategies, job tracking, background workers, and the memory-to-Postgres-to-Redis progression
- Security: JWT validation from Keycloak, Istio service mesh integration, and the difference between "auth scaffolded" and "auth enforced"
- Kubernetes deployment: Kustomize overlays, hardened Dockerfiles, and what the dev/staging/prod split actually looks like
- Kubeflow integration: how this platform plugs into an existing ML infrastructure stack

The repository is open and every code example in this article is real. The architecture is not hypothetical — it runs, it tests, and it deploys.

---

*All code referenced in this article is available in the [Private Enterprise AI Platform](https://github.com) repository. The project uses Python 3.11, FastAPI, Next.js 15, and deploys to Kubernetes with Kustomize.*
