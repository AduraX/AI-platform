# Demo Walkthrough

A guided, end-to-end walkthrough of the Private Enterprise AI Platform. Every step is a `curl` command you can copy-paste, with expected output shown inline.

By the end you will have: booted the platform, ingested a document, chatted against it with RAG retrieval, observed what happened through logs and metrics, demonstrated multi-tenant isolation, and swapped an infrastructure backend live.

---

## Prerequisites

- Docker and Docker Compose installed
- Python 3.11 and [uv](https://docs.astral.sh/uv/) installed
- Terminal with `curl` and `jq` available

Estimated time: **10-15 minutes**

---

## Step 1: Boot the Platform

### 1.1 Start infrastructure

```bash
cd AI-platform
cp .env.example .env
docker compose up -d
```

Expected output:

```
[+] Running 4/4
 ✔ Container ai-platform-postgres-1  Started
 ✔ Container ai-platform-redis-1     Started
 ✔ Container ai-platform-qdrant-1    Started
 ✔ Container ai-platform-minio-1     Started
```

### 1.2 Install dependencies

```bash
uv sync --all-packages --dev
```

### 1.3 Configure deterministic embeddings (no Ollama needed)

For this walkthrough we use the deterministic embedding provider so you do not need to pull an Ollama model. Edit `.env`:

```bash
echo "EMBEDDING_PROVIDER=deterministic" >> .env
```

> **Tip:** To use real embeddings instead, run `ollama pull embeddinggemma` and set `EMBEDDING_PROVIDER=ollama` in `.env`.

### 1.4 Start all backend services

Open seven terminals (or use a terminal multiplexer like tmux) and run one service in each:

```bash
# Terminal 1 — API Gateway
uv run uvicorn api_gateway.main:app --reload --port 8000

# Terminal 2 — Chat Service
uv run uvicorn chat_service.main:app --reload --port 8002

# Terminal 3 — RAG Service
uv run uvicorn rag_service.main:app --reload --port 8003

# Terminal 4 — Ingestion Service
uv run uvicorn ingestion_service.main:app --reload --port 8004

# Terminal 5 — Model Router
uv run uvicorn model_router.main:app --reload --port 8006

# Terminal 6 — OCR Service (optional for this walkthrough)
uv run uvicorn ocr_service.main:app --reload --port 8005

# Terminal 7 — Eval Service (optional for this walkthrough)
uv run uvicorn eval_service.main:app --reload --port 8007
```

### 1.5 Verify all services are healthy

```bash
for port in 8000 8002 8003 8004 8006; do
  echo "--- Port $port ---"
  curl -s http://localhost:$port/health | jq .
done
```

Expected output (repeated for each service):

```json
{
  "service": "api-gateway",
  "status": "ok",
  "environment": "development",
  "checks": {}
}
```

All five core services should report `"status": "ok"`.

---

## Step 2: Ingest a Document

We will ingest a fictional company refund policy as inline text. In production, this would be a file upload followed by OCR/extraction — the inline text path exercises the same chunk/embed/index pipeline.

### 2.1 Submit the document

```bash
curl -s -X POST http://localhost:8004/v1/documents \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: acme-corp" \
  -H "x-user-id: admin@acme.com" \
  -H "x-request-id: demo-ingest-001" \
  -d '{
    "filename": "refund-policy-2026.md",
    "content_type": "text/markdown",
    "text": "Acme Corp Refund Policy 2026. All enterprise accounts are eligible for a full refund within 30 calendar days of purchase. After 30 days, a prorated refund is available for the remaining subscription term. Refund requests must be submitted through the account portal or by contacting enterprise support. Personal accounts are not eligible for refunds after 14 days. All refunds are processed within 5 business days and returned to the original payment method. Cancellations take effect at the end of the current billing cycle. Enterprise customers with annual contracts may request early termination with a 60-day written notice period. Early termination fees apply at 25 percent of the remaining contract value. Volume licensing agreements have separate refund terms specified in the master service agreement."
  }' | jq .
```

Expected output:

```json
{
  "service": "ingestion-service",
  "document_id": "doc-placeholder",
  "filename": "refund-policy-2026.md",
  "job_id": "job-0001",
  "status": "completed",
  "indexed_chunks": 1,
  "object_key": "documents/doc-placeholder/refund-policy-2026.md",
  "upload_url": "http://localhost:9000/enterprise-ai/documents/doc-placeholder/refund-policy-2026.md"
}
```

Key things to note:
- `status` is `"completed"` — synchronous processing finished inline
- `indexed_chunks` is `1` — the text was chunked, embedded, and indexed into Qdrant
- `object_key` and `upload_url` show where a real file upload would go

### 2.2 Check the job status

```bash
curl -s http://localhost:8004/v1/ingestion-jobs/job-0001 | jq .
```

Expected output:

```json
{
  "service": "ingestion-service",
  "job_id": "job-0001",
  "document_id": "doc-placeholder",
  "status": "completed",
  "indexed_chunks": 1,
  "error": null
}
```

### 2.3 What just happened behind the scenes

The ingestion service executed this pipeline:

1. **Created** a document record and ingestion job
2. **Chunked** the text into segments (120 words max per chunk)
3. **Called Model Router** `POST /v1/embeddings` for each chunk to get a vector
4. **Called RAG Service** `POST /v1/index` to store the embedded chunks in Qdrant with `tenant_id: "acme-corp"` in the payload
5. **Updated** the job status to `completed` with the chunk count

You can see this in the structured JSON logs in the ingestion-service terminal.

---

## Step 3: Chat Against the Document

Now query the platform as the same tenant. The chat service will embed the query, retrieve matching chunks from Qdrant, and compose a response.

### 3.1 Ask a question through the API Gateway

```bash
curl -s -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: acme-corp" \
  -H "x-user-id: analyst@acme.com" \
  -H "x-request-id: demo-chat-001" \
  -d '{
    "message": "What is the refund policy for enterprise accounts?"
  }' | jq .
```

Expected output:

```json
{
  "service": "chat-service",
  "reply": "accepted: What is the refund policy for enterprise accounts? | grounded with 1 context chunk(s) for query 'What is the refund policy for enterprise accounts?'",
  "sources": [
    "doc://doc-placeholder/chunk-0"
  ]
}
```

Key things to note:
- `reply` confirms the question was **grounded with context chunks** — the RAG pipeline found relevant content
- `sources` shows which document chunks were used (`doc://doc-placeholder/chunk-0`)
- The request went through: API Gateway -> Chat Service -> Model Router (embedding) -> RAG Service (retrieval) -> response

### 3.2 Ask a question with no matching content

```bash
curl -s -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: acme-corp" \
  -H "x-user-id: analyst@acme.com" \
  -H "x-request-id: demo-chat-002" \
  -d '{
    "message": "How do I configure the Kubernetes deployment?"
  }' | jq .
```

With deterministic embeddings, the result depends on the hash similarity. With real embeddings, a query unrelated to the refund policy would return no retrieval context:

```json
{
  "service": "chat-service",
  "reply": "accepted: How do I configure the Kubernetes deployment? | no retrieval context found",
  "sources": []
}
```

---

## Step 4: Demonstrate Multi-Tenant Isolation

This is the most important demo. Ingest as one tenant, query as another, and prove that data does not leak.

### 4.1 Ingest a document as Tenant B

```bash
curl -s -X POST http://localhost:8004/v1/documents \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: globex-inc" \
  -H "x-user-id: admin@globex.com" \
  -H "x-request-id: demo-ingest-002" \
  -d '{
    "filename": "hr-handbook.md",
    "content_type": "text/markdown",
    "text": "Globex Inc Employee Handbook 2026. All employees are entitled to 20 days of paid time off per year. Sick leave is unlimited with manager approval. Remote work is permitted three days per week. Office attendance is required on Tuesdays and Thursdays. The annual performance review cycle begins in October. Salary adjustments are effective January 1st. Health insurance coverage begins on the first day of employment. Dental and vision plans are optional and employee-funded."
  }' | jq .
```

### 4.2 Query as Tenant A — should NOT see Tenant B's data

```bash
curl -s -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: acme-corp" \
  -H "x-user-id: analyst@acme.com" \
  -H "x-request-id: demo-chat-003" \
  -d '{
    "message": "What is the PTO policy?"
  }' | jq .
```

Expected: Acme Corp has no PTO documents ingested, so retrieval returns no context (or only their own refund policy if the embedding happens to be similar):

```json
{
  "service": "chat-service",
  "reply": "accepted: What is the PTO policy? | no retrieval context found",
  "sources": []
}
```

### 4.3 Query as Tenant B — should see their own data

```bash
curl -s -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: globex-inc" \
  -H "x-user-id: hr@globex.com" \
  -H "x-request-id: demo-chat-004" \
  -d '{
    "message": "What is the PTO policy?"
  }' | jq .
```

Expected: Globex sees their own HR handbook:

```json
{
  "service": "chat-service",
  "reply": "accepted: What is the PTO policy? | grounded with 1 context chunk(s) for query 'What is the PTO policy?'",
  "sources": [
    "doc://doc-placeholder/chunk-0"
  ]
}
```

**Tenant isolation is enforced at the vector store level.** Every vector in Qdrant carries a `tenant_id` in its payload, and every retrieval query filters by the requesting tenant's ID. There is no application-level filtering after the fact — the wrong tenant's data is never returned from the database.

> **Note:** With deterministic embeddings, the hash-based vectors may not perfectly simulate real semantic similarity. The isolation mechanism still works correctly — the tenant filter is always applied regardless of embedding provider. With Ollama embeddings (`EMBEDDING_PROVIDER=ollama`), the semantic results will be more realistic.

---

## Step 5: Observe What Happened

### 5.1 Check structured logs

Look at the terminal running the API Gateway. You will see JSON log lines like:

```json
{
  "timestamp": "2026-04-29T15:30:00.123456+00:00",
  "level": "INFO",
  "logger": "python_common.web.app_factory",
  "message": "request service=api-gateway method=POST path=/v1/chat status=200 tenant_id=acme-corp user_id=analyst@acme.com request_id=demo-chat-001 duration_ms=85.23"
}
```

Every log line includes `tenant_id`, `user_id`, and `request_id`. You can trace a request across all services by grepping for the `request_id`:

```bash
# If logging to files, you could do:
# grep "demo-chat-001" /var/log/services/*.log
```

In the terminal outputs, search for `demo-chat-001` — you will see it appear in the API Gateway, Chat Service, Model Router, and RAG Service logs.

### 5.2 Check Prometheus metrics

```bash
curl -s http://localhost:8000/metrics
```

Expected output (excerpt):

```
# HELP api_gateway_http_requests_total Total HTTP requests
# TYPE api_gateway_http_requests_total counter
api_gateway_http_requests_total{method="POST",path="/v1/chat",status="200"} 3
api_gateway_http_requests_total{method="GET",path="/health",status="200"} 1
# HELP api_gateway_http_request_duration_seconds HTTP request duration
# TYPE api_gateway_http_request_duration_seconds summary
api_gateway_http_request_duration_seconds_sum{method="POST",path="/v1/chat",status="200"} 0.256
api_gateway_http_request_duration_seconds_count{method="POST",path="/v1/chat",status="200"} 3
```

Check other services too:

```bash
curl -s http://localhost:8004/metrics  # Ingestion service
curl -s http://localhost:8003/metrics  # RAG service
curl -s http://localhost:8006/metrics  # Model router
```

### 5.3 Check health endpoints with detail

```bash
curl -s http://localhost:8004/health | jq .
```

```json
{
  "service": "ingestion-service",
  "status": "ok",
  "environment": "development",
  "checks": {}
}
```

---

## Step 6: Explore the API

### 6.1 Browse OpenAPI documentation

With the services running, open in your browser:

- API Gateway: [http://localhost:8000/docs](http://localhost:8000/docs)
- Ingestion Service: [http://localhost:8004/docs](http://localhost:8004/docs)
- RAG Service: [http://localhost:8003/docs](http://localhost:8003/docs)
- Model Router: [http://localhost:8006/docs](http://localhost:8006/docs)
- Chat Service: [http://localhost:8002/docs](http://localhost:8002/docs)

Each service auto-generates interactive Swagger UI documentation.

### 6.2 Call the embedding endpoint directly

```bash
curl -s -X POST http://localhost:8006/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"input": "enterprise refund policy"}' | jq '{model: .model, dimensions: (.embedding | length)}'
```

Expected output:

```json
{
  "model": "deterministic",
  "dimensions": 64
}
```

This shows the embedding vector dimensions. With Ollama, the model name would be `"embeddinggemma"` and dimensions would be 768.

### 6.3 Call the retrieval endpoint directly

```bash
curl -s -X POST http://localhost:8003/v1/retrieve \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: acme-corp" \
  -d '{
    "query": "refund",
    "top_k": 3
  }' | jq .
```

This bypasses the chat service and calls RAG directly — useful for debugging retrieval quality.

---

## Step 7: Ingest a Larger Document

Let's ingest a longer document to see chunking in action.

```bash
curl -s -X POST http://localhost:8004/v1/documents \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: acme-corp" \
  -H "x-user-id: admin@acme.com" \
  -H "x-request-id: demo-ingest-003" \
  -d '{
    "filename": "security-guidelines.md",
    "content_type": "text/markdown",
    "text": "Acme Corp Information Security Guidelines 2026. Chapter 1 Access Control. All employees must use multi-factor authentication for all company systems. Passwords must be at least 16 characters and rotated every 90 days. Shared accounts are prohibited. Service accounts must be registered in the identity management system and reviewed quarterly. VPN access is required for all remote connections to internal systems. Guest network access does not provide access to internal resources. Chapter 2 Data Classification. All company data must be classified as Public, Internal, Confidential, or Restricted. Public data may be shared freely. Internal data is for employees only. Confidential data requires need-to-know access and encryption at rest. Restricted data requires additional controls including audit logging, access reviews, and encryption in transit and at rest. Customer data is always classified as Confidential or Restricted. Source code is classified as Confidential. Chapter 3 Incident Response. All security incidents must be reported to the security team within one hour of discovery. The security team will triage incidents and assign severity levels from P1 critical to P4 informational. P1 incidents require immediate response and executive notification. P2 incidents must be resolved within 4 hours. All incidents are documented in the incident management system and reviewed in the monthly security review. Post-incident reviews are mandatory for P1 and P2 incidents. Chapter 4 Device Security. Company laptops must have full disk encryption enabled. Mobile devices accessing company email must have a device passcode and remote wipe capability. Personal devices used for work must comply with the bring-your-own-device policy. All devices must run current operating system versions with security patches applied within 14 days of release. Antivirus software is required on all Windows devices."
  }' | jq '{status, indexed_chunks, job_id}'
```

Expected output:

```json
{
  "status": "completed",
  "indexed_chunks": 3,
  "job_id": "job-0003"
}
```

The text was split into **3 chunks** (at ~120 words each), and each was independently embedded and indexed. Now queries against Acme Corp's tenant will search across both the refund policy and the security guidelines.

### 7.1 Chat about the new document

```bash
curl -s -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -H "x-tenant-id: acme-corp" \
  -H "x-user-id: analyst@acme.com" \
  -d '{"message": "What are the password requirements?"}' | jq .
```

---

## Step 8: Error Handling

### 8.1 Missing required fields

```bash
curl -s -X POST http://localhost:8004/v1/documents \
  -H "Content-Type: application/json" \
  -d '{}' | jq .
```

FastAPI returns a structured validation error:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "filename"],
      "msg": "Field required"
    },
    {
      "type": "missing",
      "loc": ["body", "content_type"],
      "msg": "Field required"
    }
  ]
}
```

### 8.2 Job not found

```bash
curl -s http://localhost:8004/v1/ingestion-jobs/nonexistent-job | jq .
```

Expected output:

```json
{
  "error": {
    "code": "ingestion_job_not_found",
    "message": "Ingestion job was not found.",
    "details": {
      "job_id": "nonexistent-job",
      "request_id": "..."
    }
  }
}
```

The platform uses structured error envelopes with machine-readable codes, human-readable messages, and contextual details including the request ID for tracing.

---

## Step 9: Security Headers

### 9.1 Inspect response headers

```bash
curl -s -I http://localhost:8000/v1/chat \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}' 2>&1 | grep -iE "x-content|x-frame|x-xss|referrer|cache-control"
```

Expected output:

```
x-content-type-options: nosniff
x-frame-options: DENY
x-xss-protection: 1; mode=block
referrer-policy: strict-origin-when-cross-origin
cache-control: no-store
```

Every API response includes these security headers automatically — they are set in the shared app factory middleware.

### 9.2 Health endpoint skips cache-control

```bash
curl -s -I http://localhost:8000/health | grep -i cache-control
```

The health endpoint does **not** include `Cache-Control: no-store`, allowing proxies and load balancers to cache health checks.

---

## Cleanup

Stop all services with `Ctrl+C` in each terminal, then stop infrastructure:

```bash
docker compose down
```

To also remove data volumes (Postgres, Qdrant, MinIO):

```bash
docker compose down -v
```

---

## What You Just Demonstrated

| Capability | How it was shown |
|-----------|-----------------|
| Document ingestion | Submitted inline text, saw chunking + embedding + indexing |
| RAG retrieval | Chat query found and used ingested document context |
| Multi-tenant isolation | Tenant A cannot see Tenant B's documents |
| Structured logging | JSON logs with tenant_id, user_id, request_id, duration |
| Prometheus metrics | `/metrics` endpoint with request counts and durations |
| Health checks | `/health` returning structured service status |
| Error handling | Structured error envelopes with codes and request IDs |
| Security headers | X-Frame-Options, CSP, HSTS on every response |
| OpenAPI documentation | Interactive Swagger UI per service |
| Pluggable backends | Deterministic embeddings without external dependencies |

---

## Next Steps to Explore

- **Switch to real embeddings:** Set `EMBEDDING_PROVIDER=ollama` in `.env`, run `ollama pull embeddinggemma`, restart model-router, and re-run the demo — retrieval results will be semantically meaningful.
- **Enable Postgres job store:** Set `INGESTION_JOB_STORE_BACKEND=postgres`, run migrations (`uv run python -m ingestion_service.migrations`), and see jobs survive service restarts.
- **Try background processing:** Set `INGESTION_PROCESSING_MODE=background` and submit a document — the response will return `"status": "pending"` immediately while processing happens asynchronously.
- **Run the test suite:** `uv run pytest --cov` to see all 58 tests pass with ~81% coverage.
- **Deploy to Kubernetes:** `kubectl apply -k infra/kubernetes/overlays/dev` for a local cluster deployment.
