# Private Enterprise AI Platform

A production-ready, self-hosted monorepo for enterprise AI — delivering chat, retrieval-augmented generation (RAG), document ingestion, OCR, model routing, and evaluation behind a unified API gateway with multi-tenant isolation and Keycloak SSO.

Built with **FastAPI**, **Next.js**, **PostgreSQL**, **Redis**, **Qdrant/Milvus**, and **Kubernetes** — designed to run locally with Docker Compose and scale to production on any Kubernetes cluster, including Kubeflow-integrated environments.

---

## Table of Contents

- [Architecture](#architecture)
- [Repository Layout](#repository-layout)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Running Services](#running-services)
- [Configuration Reference](#configuration-reference)
- [Database Migrations](#database-migrations)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Deployment](#deployment)
- [Kubeflow Integration](#kubeflow-integration)
- [Observability](#observability)
- [Security](#security)
- [Development Commands](#development-commands)
- [Contributing](#contributing)
- [License](#license)

---

## Architecture

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

> **Full diagrams:** See [docs/architecture/diagrams.md](docs/architecture/diagrams.md) for Mermaid sequence diagrams (chat flow, ingestion flow, auth flow), deployment topology, class diagrams, and more.

**Chat flow:** Client → API Gateway → Chat Service → Model Router (embedding) → RAG Service (retrieval from Qdrant/Milvus) → response composed with grounded context.

**Ingestion flow:** Client → Ingestion Service → chunk text → Model Router (embeddings) → RAG Service (index) → return `job_id` for async tracking.

All service-to-service calls propagate request context headers (`x-tenant-id`, `x-user-id`, `x-roles`, `x-request-id`) for multi-tenant isolation.

---

## Repository Layout

```
AI-platform/
├── apps/
│   └── frontend/                    # Next.js 15 + React 19 web application
│
├── services/
│   ├── api-gateway/                 # Public entrypoint — request routing      :8000
│   ├── chat-service/                # Chat orchestration + RAG coordination    :8002
│   ├── rag-service/                 # Vector retrieval + indexing              :8003
│   ├── ingestion-service/           # Document intake, jobs, queue, worker     :8004
│   ├── ocr-service/                 # OCR / document extraction               :8005
│   ├── model-router/                # Embedding + generation provider layer    :8006
│   └── eval-service/                # Evaluation suite management             :8007
│
├── shared/
│   └── python-common/               # Shared schemas, settings, auth, errors,
│                                    # app factory, service client, observability
│
├── infra/
│   ├── docker/                      # Shared Docker assets
│   ├── kubernetes/                  # Kustomize base + overlays (dev/staging/prod)
│   ├── kubeflow-integration/        # Istio auth, VirtualService, Keycloak Terraform
│   └── helm/                        # Helm charts (placeholder)
│
├── scripts/                         # Utility scripts (OpenAPI export, etc.)
├── docs/                            # Architecture, API docs, runbooks, articles
│
├── docker-compose.yml               # Local infrastructure (Postgres, Redis, Qdrant, MinIO)
├── pyproject.toml                   # Root workspace config, ruff, mypy, pytest
├── Makefile                         # Development commands
├── .github/                         # CI/CD workflows, Dependabot
└── .pre-commit-config.yaml          # Pre-commit hooks (ruff, mypy, detect-secrets)
```

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | >= 3.11 | Backend services |
| [uv](https://docs.astral.sh/uv/) | latest | Python workspace & dependency management |
| Node.js | >= 20 | Frontend |
| npm | >= 10 | Frontend dependencies |
| Docker + Compose | latest | Local infrastructure |
| Ollama | latest | Local embedding generation (optional) |

Install `uv` if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Quick Start

### 1. Clone and configure

```bash
git clone <repo-url> AI-platform && cd AI-platform
cp .env.example .env
```

### 2. Start infrastructure

```bash
docker compose up -d
```

This starts **PostgreSQL 16**, **Redis 7**, **Qdrant v1.9.2**, and **MinIO** (S3-compatible object storage).

### 3. Install dependencies

```bash
# Python (all services + dev tools)
uv sync --all-packages --dev

# Frontend
cd apps/frontend && npm install && cd ../..
```

### 4. Set up embeddings

**Option A — Ollama (recommended for realistic results):**

```bash
ollama pull embeddinggemma
```

**Option B — Deterministic fallback (no external model needed):**

```bash
# In .env:
EMBEDDING_PROVIDER=deterministic
```

### 5. Run database migrations

```bash
uv run python -m ingestion_service.migrations
```

### 6. Verify everything works

```bash
uv run pytest --cov
```

Expected: **58 passed, ~81% coverage**.

---

## Running Services

### Frontend

```bash
cd apps/frontend && npm run dev
# → http://localhost:3000
```

### Backend services

Start each in a separate terminal:

```bash
uv run uvicorn api_gateway.main:app        --reload --port 8000
uv run uvicorn chat_service.main:app       --reload --port 8002
uv run uvicorn rag_service.main:app        --reload --port 8003
uv run uvicorn ingestion_service.main:app  --reload --port 8004
uv run uvicorn ocr_service.main:app        --reload --port 8005
uv run uvicorn model_router.main:app       --reload --port 8006
uv run uvicorn eval_service.main:app       --reload --port 8007
```

Or use the Makefile helper:

```bash
make dev-python    # Prints all startup commands
make dev-frontend  # Starts Next.js dev server
```

### Verify services are running

```bash
curl http://localhost:8000/health
# → {"service":"api-gateway","status":"ok","environment":"development","checks":{}}
```

Each service exposes `/health` and `/metrics` (Prometheus format).

---

## Configuration Reference

All configuration is via environment variables. See `.env.example` for the full list.

### Key settings

| Variable | Default | Options | Description |
|----------|---------|---------|-------------|
| `ENVIRONMENT` | `development` | any string | Runtime environment label |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | Structured JSON log level |
| `AUTH_ENABLED` | `false` | `true`, `false` | Enable Keycloak JWT validation |
| `CORS_ALLOWED_ORIGINS` | `["http://localhost:3000"]` | JSON array | CORS allowed origins |
| `VECTOR_STORE_BACKEND` | `qdrant` | `qdrant`, `milvus` | Vector database backend |
| `EMBEDDING_PROVIDER` | `ollama` | `ollama`, `deterministic` | Embedding provider |
| `EMBEDDING_MODEL` | `embeddinggemma` | any Ollama model | Embedding model name |
| `INGESTION_JOB_STORE_BACKEND` | `memory` | `memory`, `postgres` | Job metadata storage |
| `INGESTION_QUEUE_BACKEND` | `memory` | `memory`, `redis` | Ingestion queue backend |
| `INGESTION_PROCESSING_MODE` | `sync` | `sync`, `background` | Inline vs. async processing |

### Infrastructure endpoints

| Variable | Default |
|----------|---------|
| `POSTGRES_HOST` | `localhost` |
| `REDIS_HOST` | `localhost` |
| `QDRANT_HOST` / `QDRANT_PORT` | `localhost` / `6333` |
| `MILVUS_HOST` / `MILVUS_PORT` | `localhost` / `19530` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` |
| `OBJECT_STORAGE_ENDPOINT` | `http://localhost:9000` |

### Keycloak / Auth

| Variable | Default |
|----------|---------|
| `KEYCLOAK_URL` | `http://localhost:8081` |
| `KEYCLOAK_REALM` | `enterprise-ai` |
| `KEYCLOAK_CLIENT_ID` | `enterprise-ai-web` |
| `KEYCLOAK_VERIFY_SSL` | `true` |

---

## Database Migrations

The ingestion service uses incremental SQL migrations tracked in a `schema_migrations` table (idempotent — safe to re-run):

```bash
uv run python -m ingestion_service.migrations
# → Applied 2 new migration(s).
```

Migration files: `services/ingestion-service/migrations/*.sql`

---

## API Reference

All services auto-generate OpenAPI specs. With a service running, visit:

- Swagger UI: `http://localhost:<port>/docs`
- ReDoc: `http://localhost:<port>/redoc`
- OpenAPI JSON: `http://localhost:<port>/openapi.json`

To export all specs at once:

```bash
uv run python scripts/export_openapi.py
# → docs/api/openapi/<service>.json
```

### Core endpoints

| Method | Path | Service | Description |
|--------|------|---------|-------------|
| `GET` | `/health` | All | Health check with component status |
| `GET` | `/metrics` | All | Prometheus metrics |
| `POST` | `/v1/chat` | API Gateway → Chat | Chat with RAG context |
| `POST` | `/v1/documents` | Ingestion | Create document + start ingestion |
| `POST` | `/v1/documents:process` | Ingestion | Synchronous document processing |
| `GET` | `/v1/ingestion-jobs/{id}` | Ingestion | Check job status |
| `POST` | `/v1/retrieve` | RAG | Semantic search with embeddings |
| `POST` | `/v1/index` | RAG | Index document chunks |
| `POST` | `/v1/embeddings` | Model Router | Generate embeddings |
| `POST` | `/v1/generate` | Model Router | Text generation (scaffolded) |
| `POST` | `/internal/ocr` | OCR | Document extraction (scaffolded) |
| `POST` | `/v1/evals` | Eval | Create evaluation suite (scaffolded) |

### Request context headers

All internal requests propagate these headers for multi-tenant isolation:

```
x-tenant-id      Tenant identifier (default: "default")
x-user-id        User identifier (default: "anonymous")
x-roles          Comma-separated roles
x-request-id     Correlation ID (auto-generated if missing)
```

When `AUTH_ENABLED=true`, JWT claims from Keycloak override these headers.

---

## Testing

### Python tests

```bash
# Full suite with coverage
uv run pytest --cov

# Specific service
uv run pytest services/ingestion-service/tests

# Only unit tests (skip integration)
uv run pytest -m "not integration"
```

### Frontend tests

```bash
cd apps/frontend
npm test              # Run once
npm run test:watch    # Watch mode
npm run type-check    # TypeScript validation
npm run lint          # ESLint
```

### Test markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.integration` | Requires live infrastructure (Postgres, Redis, etc.) |
| `@pytest.mark.slow` | Long-running tests |

### Coverage

Coverage is enforced at **60% minimum**. Current: **~81%**. Reports are generated as XML for CI integration.

---

## Deployment

### Docker

Each service has a hardened Dockerfile with:
- Non-root user (`appuser`, UID 1001)
- `HEALTHCHECK` instruction
- Multi-stage builds (frontend)

Build all images:

```bash
docker build -f services/api-gateway/Dockerfile -t enterprise-ai/api-gateway .
docker build -f services/chat-service/Dockerfile -t enterprise-ai/chat-service .
# ... repeat for each service
docker build -f apps/frontend/Dockerfile -t enterprise-ai/frontend .
```

### Kubernetes

Full Kustomize manifests are provided with three environment overlays:

```bash
# Development (1 replica, debug logging, auth disabled)
kubectl apply -k infra/kubernetes/overlays/dev

# Staging
kubectl apply -k infra/kubernetes/overlays/staging

# Production (3 replicas, resource limits, auth enabled)
kubectl apply -k infra/kubernetes/overlays/prod
```

Each deployment includes:
- Resource requests/limits
- Liveness, readiness, and startup probes
- Non-root security context
- ConfigMap + Secret injection
- NetworkPolicy for namespace isolation

> **Important:** Update `infra/kubernetes/base/secrets.yaml` with real credentials before deploying to any shared environment.

---

## Kubeflow Integration

The platform integrates with [Kubeflow4x Phase-1](infra/kubeflow-integration/README.md) deployments that use Keycloak + Istio:

### 1. Register the OIDC client

```bash
cd infra/kubeflow-integration
terraform init
terraform apply \
  -var="keycloak_url=https://keycloak.example.com" \
  -var="ai_platform_url=https://ai-platform.example.com"
```

### 2. Update Istio auth placeholders

Replace `__KEYCLOAK_ISSUER__` and `__KEYCLOAK_JWKS_URI__` in `infra/kubeflow-integration/istio-auth.yaml`.

### 3. Deploy with Istio integration

```bash
kubectl apply -k infra/kubeflow-integration
```

This configures:
- **Istio RequestAuthentication** — JWT validation from Keycloak with claim-to-header mapping
- **AuthorizationPolicy** — denies unauthenticated requests, delegates browser flows to oauth2-proxy
- **VirtualService** — routes `/api/v1/*` to the API Gateway and `/*` to the frontend

See [infra/kubeflow-integration/README.md](infra/kubeflow-integration/README.md) for full details.

---

## Observability

### Structured logging

All services emit **JSON-structured logs** to stdout:

```json
{
  "timestamp": "2026-04-29T12:00:00+00:00",
  "level": "INFO",
  "logger": "python_common.web.app_factory",
  "message": "request service=api-gateway method=POST path=/v1/chat status=200 ...",
  "service": "api-gateway",
  "tenant_id": "acme-corp",
  "request_id": "abc-123",
  "duration_ms": 42.5
}
```

### Prometheus metrics

Every service exposes a `/metrics` endpoint with:

```
<service>_http_requests_total{method, path, status}
<service>_http_request_duration_seconds_sum{method, path, status}
<service>_http_request_duration_seconds_count{method, path, status}
```

### Health checks

`GET /health` returns service status and component checks:

```json
{
  "service": "ingestion-service",
  "status": "ok",
  "environment": "production",
  "checks": {}
}
```

---

## Security

### Authentication

- **JWT validation** from Keycloak via JWKS (RS256), with 5-minute key cache
- When `AUTH_ENABLED=true`, JWT claims (`email`, `tenant_id`, `realm_access.roles`) override raw request headers
- When disabled, services accept `x-tenant-id` / `x-user-id` headers directly (for local development)

### Headers

All responses include:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Cache-Control: no-store  (API responses only)
```

### CORS

Configurable via `CORS_ALLOWED_ORIGINS`. Defaults to `["http://localhost:3000"]`.

### Pre-commit hooks

```bash
pip install pre-commit
pre-commit install
```

Runs ruff (lint + format), mypy, and `detect-secrets` on every commit.

### Dependency scanning

Dependabot is configured for Python, npm, Docker, and GitHub Actions dependencies (weekly updates).

---

## Development Commands

```bash
make install-python     # Install all Python packages + dev tools
make install-frontend   # Install frontend dependencies
make lock               # Regenerate uv.lock
make test               # Run all Python tests
make lint               # Lint Python code (ruff)
make fmt                # Format Python code (ruff)
make dev-python         # Print backend service startup commands
make dev-frontend       # Start Next.js dev server
make docker-up          # Start infrastructure (Postgres, Redis, Qdrant, MinIO)
make docker-down        # Stop infrastructure
```

### Additional commands

```bash
# Type checking
uv run mypy .                                    # Python
cd apps/frontend && npm run type-check           # TypeScript

# OpenAPI export
uv run python scripts/export_openapi.py

# Database migrations
uv run python -m ingestion_service.migrations

# Pre-commit (all hooks)
pre-commit run --all-files
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, TypeScript |
| Backend | Python 3.11, FastAPI 0.115, Uvicorn |
| Database | PostgreSQL 16 (metadata), Redis 7 (cache/queue) |
| Vector Store | Qdrant v1.9 (default), Milvus (alternative) |
| Object Storage | MinIO (S3-compatible) |
| Auth | Keycloak (OIDC/JWT), Istio (service mesh) |
| Model Serving | Ollama (local), vLLM (production) |
| Infrastructure | Docker Compose (dev), Kubernetes + Kustomize (prod) |
| CI/CD | GitHub Actions, Dependabot, pre-commit |
| Observability | Structured JSON logging, Prometheus metrics |
| Code Quality | Ruff (lint/format), mypy (types), pytest-cov (coverage) |

---

## Contributing

1. Install pre-commit hooks: `pre-commit install`
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and ensure tests pass: `uv run pytest --cov`
4. Lint and format: `make lint && make fmt`
5. Commit with a descriptive message
6. Open a pull request

### Code style

- Python: enforced by ruff (`E,F,I,N,UP,S,B,C4,SIM,TCH,RUF`), formatted with `ruff format`
- TypeScript: enforced by ESLint (`next/core-web-vitals`)
- Types: mypy for Python, `tsc --noEmit` for TypeScript
- Tests: pytest (Python), Vitest (frontend), minimum 60% coverage

---

## License

This project is provided as a reference architecture. See `LICENSE` for terms.
