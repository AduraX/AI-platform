# Architecture Diagrams

A mixture of ASCII art for structural overviews and Mermaid for interactive flows. Mermaid diagrams render natively on GitHub, GitLab, Notion, and most Markdown viewers.

---

## System Overview

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
+---------+  +---------+
| Qdrant/ |  | MinIO   |
| Milvus  |  | (S3)    |
+---------+  +---------+

     +----------+  +---------+
     | Postgres |  |  Redis  |
     +----------+  +---------+
```

---

## Service Ports Quick Reference

```
 Service               Port    Role
 ───────────────────────────────────────────
 Frontend              3000    Next.js web app
 API Gateway           8000    Public entrypoint
 Chat Service          8002    Chat + RAG orchestration
 RAG Service           8003    Vector retrieval/indexing
 Ingestion Service     8004    Document pipeline + jobs
 OCR Service           8005    Text extraction
 Model Router          8006    Embedding/generation
 Eval Service          8007    Evaluation suites
```

---

## Chat Flow

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant GW as API Gateway
    participant CS as Chat Service
    participant MR as Model Router
    participant RS as RAG Service
    participant QD as Qdrant

    User->>FE: "What is the refund policy?"
    FE->>GW: POST /v1/chat/stream
    Note over FE,GW: Headers: x-tenant-id, x-user-id

    GW->>CS: POST /v1/chat/stream (proxy)

    CS->>MR: POST /v1/embeddings
    MR-->>CS: embedding[768]

    CS->>RS: POST /v1/retrieve
    Note over CS,RS: query_embedding + tenant_id
    RS->>QD: Search with tenant filter
    QD-->>RS: Top-K chunks
    RS-->>CS: RetrieveResponse

    CS-->>GW: SSE: status, source, token..., done
    GW-->>FE: SSE stream (proxied)
    FE-->>User: Streaming response with sources
```

---

## Document Ingestion Flow

```mermaid
sequenceDiagram
    actor User
    participant FE as Frontend
    participant IS as Ingestion Service
    participant S3 as MinIO
    participant OCR as OCR Service
    participant MR as Model Router
    participant RS as RAG Service
    participant QD as Qdrant

    User->>FE: Upload document
    FE->>IS: POST /v1/documents/upload (multipart)

    IS->>S3: Store file
    S3-->>IS: object_key

    IS->>IS: Create job (status: pending)

    IS->>OCR: POST /internal/ocr
    OCR->>S3: Download file
    OCR-->>IS: extracted_text

    loop For each chunk
        IS->>IS: Split text into chunks
        IS->>MR: POST /v1/embeddings
        MR-->>IS: embedding[768]
    end

    IS->>RS: POST /v1/index (batch)
    RS->>QD: Upsert vectors + metadata
    QD-->>RS: indexed_count
    RS-->>IS: VectorIndexResponse

    IS->>IS: Update job (status: completed)
    IS-->>FE: DocumentCreatedResponse
    FE-->>User: Show job status + chunk count
```

---

## Inline Text Ingestion (Simplified)

```
 POST /v1/documents        Chunk Text         Embed Chunks        Index Batch         Update Job
 { text: "..." }     -->  (120 words/chunk) --> Model Router  -->  RAG Service  -->  status: completed
                                                /v1/embeddings      /v1/index         indexed_chunks: N
```

---

## Multi-Tenant Data Isolation

```
 +-----------------------+        +-----------------------+
 |      Tenant A         |        |      Tenant B         |
 |     (acme-corp)       |        |     (globex-inc)      |
 +-----------+-----------+        +-----------+-----------+
             |                                |
             v                                v
    +--------+--------+             +--------+--------+
    | RAG: retrieve    |             | RAG: retrieve    |
    | filter:          |             | filter:          |
    | tenant_id =      |             | tenant_id =      |
    |   "acme-corp"    |             |   "globex-inc"   |
    +--------+--------+             +--------+--------+
             |                                |
             v                                v
  +----------+----------+         +-----------+---------+
  | Qdrant vectors      |         | Qdrant vectors      |
  | tenant_id=acme-corp |         | tenant_id=globex-inc|
  +---------------------+         +---------------------+

  Tenant A CANNOT see Tenant B vectors — filtered at the query level.
```

---

## Authentication Flow (Keycloak + Istio)

```mermaid
sequenceDiagram
    actor User
    participant Browser
    participant Istio as Istio Ingress
    participant OAuth as oauth2-proxy
    participant KC as Keycloak
    participant GW as API Gateway
    participant Svc as Backend Service

    User->>Browser: Navigate to platform
    Browser->>Istio: GET /
    Istio->>Istio: No JWT - DENY

    Istio->>OAuth: ExtAuthz check
    OAuth->>Browser: 302 Redirect to Keycloak
    Browser->>KC: Login page
    User->>KC: Enter credentials
    KC->>Browser: 302 + authorization code
    Browser->>OAuth: /oauth2/callback
    OAuth->>KC: Exchange code for JWT
    KC-->>OAuth: JWT (access + id token)
    OAuth->>Browser: Set cookie + redirect

    Browser->>Istio: GET / (with JWT)
    Istio->>Istio: Validate JWT (JWKS)
    Note over Istio: Extract claims to headers<br/>email to x-user-id<br/>tenant_id to x-tenant-id

    Istio->>GW: Forward with context headers
    GW->>Svc: Forward to service
    Svc-->>GW: Response
    GW-->>Browser: Response
```

---

## Kubernetes Deployment Topology

```
 +===========================================================+
 |                    Kubernetes Cluster                       |
 |                                                             |
 |  +--- istio-system ----------------------------------+     |
 |  |  Istio Ingress Gateway                            |     |
 |  |  RequestAuthentication (Keycloak JWT)              |     |
 |  |  AuthorizationPolicy (DENY unauthed + oauth2)      |     |
 |  +---------------------------------------------------+     |
 |         |                                                   |
 |         v                                                   |
 |  +--- enterprise-ai --------------------------------+      |
 |  |                                                   |      |
 |  |  Deployments (x2 replicas each):                  |      |
 |  |    api-gateway        :8000                       |      |
 |  |    chat-service       :8002                       |      |
 |  |    rag-service        :8003                       |      |
 |  |    ingestion-service  :8004                       |      |
 |  |    ocr-service        :8005                       |      |
 |  |    model-router       :8006                       |      |
 |  |    eval-service       :8007                       |      |
 |  |    frontend           :3000                       |      |
 |  |                                                   |      |
 |  |  ConfigMap: ai-platform-config                    |      |
 |  |  Secret:    ai-platform-secrets                   |      |
 |  |  NetworkPolicy: namespace + istio ingress only    |      |
 |  +---------------------------------------------------+      |
 |                                                             |
 |  Overlays:                                                  |
 |    dev     = 1 replica, DEBUG, auth off                     |
 |    staging = 2 replicas, INFO                               |
 |    prod    = 3 replicas, resource limits                    |
 +===========================================================+

         |                              |
    +----v----+                   +-----v-----+
    | Keycloak|                   | Load      |
    | (OIDC)  |                   | Balancer  |
    +---------+                   +-----------+
```

---

## Vector Store Abstraction

```mermaid
classDiagram
    class VectorStore {
        <<Protocol>>
        +backend_name: str
        +retrieve(query, tenant_id, query_embedding, top_k) list~RetrievalContext~
        +index(document_id, tenant_id, chunks) int
    }

    class QdrantVectorStore {
        +backend_name = "qdrant"
        -client: QdrantClient
        -collection_name: str
        +retrieve() list~RetrievalContext~
        +index() int
    }

    class MilvusVectorStore {
        +backend_name = "milvus"
        -host: str
        -port: int
        +retrieve() list~RetrievalContext~
        +index() int
    }

    class create_vector_store {
        <<factory>>
        +settings -> VectorStore
    }

    VectorStore <|.. QdrantVectorStore
    VectorStore <|.. MilvusVectorStore
    create_vector_store --> VectorStore
```

---

## Ingestion Job State Machine

```mermaid
stateDiagram-v2
    [*] --> pending: Job created

    pending --> completed: Sync processing succeeds
    pending --> failed: Sync processing fails
    pending --> queued: Background mode

    queued --> processing: Worker dequeues
    processing --> completed: chunk/embed/index succeeds
    processing --> failed: Pipeline error

    completed --> [*]
    failed --> [*]

    note right of pending: In-memory or PostgreSQL
    note right of queued: In-memory or Redis
```

---

## Request Context Propagation

```
 Browser
    |
    |  Authorization: Bearer <JWT>
    v
 +--+-----------+
 | Istio /      |   Extract JWT claims:
 | API Gateway  | ─────────────────────────────+
 +--------------+                              |
    |                                          v
    |  x-tenant-id: acme-corp          +--------------+
    |  x-user-id: user@acme.com        | RequestContext|
    |  x-roles: admin,user             |  tenant_id   |
    |  x-request-id: abc-123           |  user_id     |
    v                                  |  roles       |
 +--+-----------+                      |  request_id  |
 | Chat Service | ── forwards ──────>  +--------------+
 +--------------+    same headers            |
    |                                        v
    v                                 All downstream
 +--+-----------+                     services receive
 | RAG Service  |                     the same context
 +--------------+
```

---

## CI/CD Pipeline

```
 Pull Request                                  Main Branch
 ─────────────────────────────────────         ────────────────────
 Push / PR
    |
    +──> [Lint]                                [Coverage Report]
    |     ruff check + format                       ^
    |     mypy type check                           |
    |        |                                      |
    |        v                                      |
    +──> [Test] ────────────────────────────────────+
    |     pytest --cov (60% min)
    |
    +──> [Frontend Lint]
    |     ESLint + tsc --noEmit
    |        |
    |        v
    +──> [Frontend Test]
    |     Vitest
    |
    +──> [Docker Build] ────────────> [Push Images to GHCR]
          8 service images
          (build only on PR,
           push on main)
```
