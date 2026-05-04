import pytest
from pydantic import ValidationError
from python_common import AppSettings


def test_vector_store_backend_defaults_to_qdrant() -> None:
    settings = AppSettings()

    assert settings.vector_store_backend == "qdrant"
    assert settings.vector_collection_name == "document_chunks"
    assert settings.retrieval_top_k == 5
    assert settings.qdrant_port == 6333
    assert settings.milvus_port == 19530
    assert settings.embedding_provider == "ollama"
    assert settings.embedding_model == "embeddinggemma"
    assert settings.ingestion_job_store_backend == "memory"
    assert settings.ingestion_processing_mode == "sync"
    assert settings.ingestion_queue_backend == "memory"
    assert settings.object_storage_bucket == "enterprise-ai"


def test_vector_store_backend_accepts_milvus() -> None:
    settings = AppSettings(vector_store_backend="milvus", milvus_host="milvus")

    assert settings.vector_store_backend == "milvus"
    assert settings.milvus_host == "milvus"


def test_vector_store_backend_rejects_unknown_backend() -> None:
    with pytest.raises(ValidationError):
        AppSettings(vector_store_backend="pinecone")


def test_embedding_provider_rejects_unknown_provider() -> None:
    with pytest.raises(ValidationError):
        AppSettings(embedding_provider="unknown")


def test_ingestion_job_store_rejects_unknown_backend() -> None:
    with pytest.raises(ValidationError):
        AppSettings(ingestion_job_store_backend="unknown")


def test_ingestion_queue_rejects_unknown_backend() -> None:
    with pytest.raises(ValidationError):
        AppSettings(ingestion_queue_backend="unknown")
