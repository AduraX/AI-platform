"""Integration tests for Ollama embedding provider.

Requires: ollama running with embeddinggemma model pulled
Run with: uv run pytest -m integration tests/integration/test_ollama_embeddings.py
"""
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.slow]


@pytest.fixture
def ollama_provider():
    from model_router.embeddings import OllamaEmbeddingProvider
    return OllamaEmbeddingProvider(
        base_url="http://localhost:11434",
        model="embeddinggemma",
    )


@pytest.mark.asyncio
async def test_embed_text(ollama_provider):
    embedding = await ollama_provider.embed("What is the refund policy?")
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(x, float) for x in embedding)


@pytest.mark.asyncio
async def test_embed_different_texts_produce_different_vectors(ollama_provider):
    emb1 = await ollama_provider.embed("refund policy")
    emb2 = await ollama_provider.embed("quantum physics")
    assert emb1 != emb2


@pytest.mark.asyncio
async def test_embed_similar_texts_produce_similar_vectors(ollama_provider):
    emb1 = await ollama_provider.embed("What is the refund policy?")
    emb2 = await ollama_provider.embed("Tell me about refunds")
    # Cosine similarity should be relatively high for similar texts
    dot = sum(a * b for a, b in zip(emb1, emb2, strict=True))
    mag1 = sum(a * a for a in emb1) ** 0.5
    mag2 = sum(b * b for b in emb2) ** 0.5
    cosine_sim = dot / (mag1 * mag2) if mag1 and mag2 else 0
    assert cosine_sim > 0.5  # Similar texts should have reasonable similarity
