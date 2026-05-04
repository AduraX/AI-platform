# Private Enterprise AI Platform

## Project Summary

Private Enterprise AI Platform is a production-oriented, self-hosted AI system designed for secure internal knowledge access, document intelligence, and multi-user conversational AI. The platform combines a ChatGPT-like user experience with enterprise retrieval, OCR-driven document understanding, model routing, evaluation workflows, and Kubernetes-ready deployment.

The goal of the project is to provide a portfolio-grade reference architecture for building enterprise AI systems that are practical to operate, modular by design, and extensible across local and hosted model backends.

## Objectives

- Deliver a secure internal AI assistant for enterprise users
- Support retrieval-augmented generation over private documents
- Process scanned PDFs and images through OCR and document intelligence workflows
- Enable multi-user access with authentication and role-based access control
- Route requests across local and scalable inference backends
- Provide observability, evaluation, and operational readiness from the start
- Remain suitable for local development while scaling cleanly to Kubernetes

## Core Capabilities

### 1. Chat Interface

The platform includes a web application that offers a ChatGPT-like experience for internal users. Conversations are stored and managed by a dedicated chat service that coordinates retrieval, model inference, and response streaming.

### 2. Retrieval-Augmented Generation

Users can ask questions against internal documents. The platform retrieves relevant chunks from a vector store, applies tenant-aware access filtering, and supplies grounded context to the model before generation.

### 3. OCR and Document Intelligence

Documents such as scanned PDFs and images are processed asynchronously. OCR and layout-aware extraction transform raw files into structured text artifacts that can be chunked, embedded, and indexed for search and chat.

### 4. Model Routing

A dedicated model router abstracts model providers behind one internal contract. This allows the system to switch between local development models, scalable self-hosted inference, and hosted APIs without changing upstream application logic.

### 5. Enterprise Security

Authentication and authorization are built around Keycloak and RBAC-aware request handling. The architecture is designed for tenant-aware enforcement and auditability rather than consumer-grade convenience flows.

### 6. Evaluation and Observability

The platform includes service boundaries for offline evaluation, usage tracking, latency monitoring, and operational dashboards. This makes it possible to compare prompt strategies, retrieval quality, and model behavior before changes are rolled out.

## Technology Stack

### Frontend

- Next.js
- React

### Backend

- FastAPI
- Python 3.11
- `uv` for Python workspace management and packaging

### Identity and Access

- Keycloak
- OIDC
- RBAC

### Data and State

- Postgres for system-of-record metadata
- Redis for caching, rate limiting, and short-lived operational state
- Tunable vector store backend with Qdrant as the local default and Milvus as an alternate option
- Object storage for raw files and derived document artifacts

### Model Serving

- Ollama for local development, lightweight local inference, and default embedding generation
- vLLM for scalable self-hosted inference
- Optional hosted provider integration through the model router

### Platform and Operations

- Docker and Docker Compose for local development
- Kubernetes for deployment
- Helm and Kustomize-ready infrastructure layout
- Prometheus and Grafana for monitoring

## High-Level Architecture

The platform is structured as a modular monorepo with clear separation between the frontend, backend services, shared libraries, and deployment assets.

### Primary Services

- Frontend web application
- API gateway
- Chat service
- RAG service
- Ingestion service
- OCR service
- Model router service
- Evaluation service

### Supporting Infrastructure

- Keycloak for identity and access management
- Postgres for relational persistence
- Redis for transient state and caching
- Qdrant or Milvus for embeddings and semantic retrieval
- Object storage for source documents and derived artifacts
- Prometheus and Grafana for observability

## Service Responsibilities

### Frontend Web App

Provides the user-facing experience for chat, document upload, administration, and evaluation views. It communicates only with the API gateway and does not directly access internal services or databases.

### API Gateway

Acts as the public backend entrypoint. It validates authentication context, applies coarse-grained authorization and routing rules, and forwards requests to internal domain services.

### Chat Service

Manages chat sessions, messages, response streaming, and orchestration between retrieval and inference. This service is responsible for the main interactive user experience.

### RAG Service

Handles retrieval logic across vector search and metadata filters. It prepares grounded context packages for the chat service while enforcing tenant and document-level access constraints.

### Ingestion Service

Owns document registration, upload workflows, version tracking, and async job dispatch for OCR, chunking, embedding, and indexing.

### OCR Service

Processes scanned and image-based documents into structured outputs such as extracted text, page-level anchors, and layout artifacts.

### Model Router

Abstracts model access behind one internal API. It chooses between available inference backends based on environment, policy, and future routing rules. Embedding requests are provider-backed, with Ollama as the default local provider and an explicit deterministic fallback for offline contract tests.

### Evaluation Service

Executes benchmark and regression workflows for model behavior, retrieval quality, and prompt strategies. It supports safer iteration and deployment confidence.

## Data Flow

### User Query Flow

1. A user authenticates through Keycloak.
2. The frontend sends requests to the API gateway with the user token.
3. The gateway forwards the request to the chat service.
4. The chat service requests a query embedding from the model router.
5. The chat service requests relevant context from the RAG service with the query embedding.
6. The RAG service retrieves matching chunks from the configured vector store and metadata filters from Postgres.
7. The chat service sends the grounded prompt to the model router.
8. The model router selects Ollama, vLLM, or another configured provider.
9. The generated answer is streamed back to the user through the gateway.

### Document Ingestion Flow

1. A document is uploaded through the frontend and API gateway.
2. The ingestion service creates an ingestion job, returns object-storage upload metadata, and records metadata in Postgres when the Postgres job store is enabled. In the current scaffold path, inline text can also be submitted directly with document metadata.
3. An async job is created for OCR and parsing when source files require extraction.
4. The OCR service extracts text and structural artifacts.
5. The ingestion pipeline chunks available text and requests embeddings through the model router.
6. Embedded chunks are sent to the RAG service indexing endpoint and stored in the configured vector store, while metadata remains in Postgres.
7. The document becomes searchable and available for RAG, and ingestion job status can be queried by job ID. Processing can run synchronously or through the FastAPI background-task scaffold depending on `INGESTION_PROCESSING_MODE`; Redis queueing is available as the durable-worker handoff point.

## Synchronous and Asynchronous Workloads

### Synchronous

- User login and token validation
- Chat requests
- Retrieval during interactive chat
- Model inference and streaming
- Read-oriented admin and document status endpoints

### Asynchronous

- OCR processing
- Parsing and chunking
- Embedding generation for ingestion
- Vector indexing and backfills
- Evaluation runs
- Analytics aggregation and background enrichment

This split keeps the user path responsive while moving long-running or retryable operations out of the request path.

## Storage Design

### Postgres

Used for tenants, users, roles, chat metadata, messages, document metadata, job state, model registry data, evaluation runs, and audit records.

### Redis

Used for caching, transient orchestration state, rate limiting, and future queue or event coordination where appropriate.

### Vector Store

Configured through `VECTOR_STORE_BACKEND`, with `qdrant` as the local development default and `milvus` available for deployments that prefer the Milvus ecosystem. Indexing requests store embedded document chunks in the selected backend. Retrieval requests carry a query embedding and optional top-k value; the RAG service applies tenant-aware filtering when querying the selected backend.

### Qdrant

Used for embeddings and semantic retrieval, with tenant-aware metadata payloads to support access-filtered search.

### Milvus

Available as an alternate vector backend for teams that need Milvus-native indexing, scaling, and operational patterns.

### Object Storage

Used for uploaded files, OCR outputs, extracted artifacts, chunking outputs, and large evaluation datasets.

## Deployment Strategy

The system is designed for local development first and production deployment on Kubernetes.

### Local Development

- Docker Compose for Postgres, Redis, Qdrant, and object storage, with Milvus supported through vector backend configuration
- Ollama for local model serving
- Next.js frontend and FastAPI services run directly in development mode
- `uv` manages Python dependencies and workspace execution

### Production

- Stateless services deployed as Kubernetes workloads
- vLLM deployed on GPU-capable nodes for scalable inference
- Keycloak deployed as critical identity infrastructure
- Prometheus and Grafana collect metrics and dashboards
- Helm and Kustomize-compatible infra layout supports environment overlays

## Repository Structure

The monorepo is organized to keep responsibilities separated and service ownership explicit.

- `apps/frontend` contains the Next.js application
- `services/` contains backend domain services
- `shared/python-common` contains reusable Python code for config and shared primitives
- `infra/` contains Docker, Kubernetes, and Helm-related assets
- `docs/` contains architecture, API, and operational documentation

## Engineering Principles

- Production-oriented service boundaries
- Clear separation of concerns
- Minimal shared code across services
- Local developer experience without sacrificing deployment realism
- Explicit infrastructure layout for future CI/CD and Kubernetes rollout
- Replaceable model backends through a stable routing layer

## Current State of the Project

The repository currently contains:

- A monorepo scaffold aligned to the target architecture
- A Next.js frontend starter
- FastAPI starter services for gateway, chat, retrieval, ingestion, OCR, model routing, and evaluation
- Shared Python package structure
- Dockerfiles for frontend and services
- Docker Compose for core local dependencies
- Kubernetes base and overlay placeholders
- `uv` workspace configuration for Python packaging and installation

## Planned Next Steps

- Add lockfile generation and full dependency sync through `uv`
- Introduce shared API contracts and common service bootstrap patterns
- Add real Keycloak and Ollama integration in local infrastructure
- Define database schemas and migrations
- Implement ingestion and retrieval pipelines
- Add streaming chat orchestration
- Build evaluation workflows and observability instrumentation
- Extend deployment assets for staging and production

## Conclusion

Private Enterprise AI Platform is designed as a realistic enterprise AI foundation rather than a demo application. Its architecture emphasizes security, modularity, observability, and deployability. The project demonstrates how to combine conversational AI, retrieval, OCR, model routing, and infrastructure discipline into one coherent platform that can evolve from local development into a production-grade system.
