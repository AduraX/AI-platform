from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    service_name: str = "service"
    environment: str = "development"
    log_level: str = "INFO"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "enterprise_ai"
    postgres_user: str = "enterprise_ai"
    postgres_password: str = "enterprise_ai"
    ingestion_job_store_backend: Literal["memory", "postgres"] = "memory"
    ingestion_processing_mode: Literal["sync", "background"] = "sync"

    redis_host: str = "localhost"
    redis_port: int = 6379
    ingestion_queue_backend: Literal["memory", "redis"] = "memory"

    object_storage_endpoint: str = "http://localhost:9000"
    object_storage_access_key: str = "minioadmin"
    object_storage_secret_key: str = "minioadmin"
    object_storage_bucket: str = "enterprise-ai"

    vector_store_backend: Literal["qdrant", "milvus"] = "qdrant"
    vector_collection_name: str = "document_chunks"
    vector_embedding_field: str = "embedding"
    vector_content_payload_key: str = "content"
    vector_source_payload_key: str = "source"
    vector_tenant_payload_key: str = "tenant_id"
    retrieval_top_k: int = 5
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    milvus_host: str = "localhost"
    milvus_port: int = 19530

    keycloak_url: str = "http://localhost:8081"
    keycloak_realm: str = "enterprise-ai"
    keycloak_client_id: str = "enterprise-ai-web"

    api_gateway_base_url: str = "http://localhost:8000"
    chat_service_base_url: str = "http://localhost:8002"
    rag_service_base_url: str = "http://localhost:8003"
    ingestion_service_base_url: str = "http://localhost:8004"
    ocr_service_base_url: str = "http://localhost:8005"
    model_router_base_url: str = "http://localhost:8006"
    eval_service_base_url: str = "http://localhost:8007"

    # Security
    auth_enabled: bool = False
    cors_allowed_origins: list[str] = ["http://localhost:3000"]
    rate_limit_per_minute: int = 60
    keycloak_verify_ssl: bool = True

    request_timeout_seconds: float = 10.0
    upstream_retry_count: int = 2

    ollama_base_url: str = "http://localhost:11434"
    vllm_base_url: str = "http://localhost:8001"
    embedding_provider: Literal["deterministic", "ollama"] = "ollama"
    embedding_model: str = "embeddinggemma"

    # Tracing
    tracing_enabled: bool = False
    otlp_endpoint: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
