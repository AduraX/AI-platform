import anyio
import httpx
from model_router.embeddings import OllamaEmbeddingProvider
from model_router.routes import build_router
from python_common import AppSettings
from python_common.schemas import EmbeddingRequest


def test_embeddings_returns_deterministic_vector() -> None:
    router = build_router(
        AppSettings(
            service_name="model-router",
            embedding_provider="deterministic",
            embedding_model="embed-test",
        )
    )
    endpoint = next(route.endpoint for route in router.routes if route.path == "/v1/embeddings")

    first = anyio.run(lambda: endpoint(payload=EmbeddingRequest(input="policy")))
    second = anyio.run(lambda: endpoint(payload=EmbeddingRequest(input="policy")))

    assert first.service == "model-router"
    assert first.model == "embed-test"
    assert first.embedding == second.embedding
    assert len(first.embedding) == 8


def test_ollama_embedding_provider_calls_embed_endpoint(monkeypatch) -> None:
    class DummyResponse:
        text = ""
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "model": "embeddinggemma",
                "embeddings": [[0.1, 0.2, 0.3]],
            }

    class DummyAsyncClient:
        def __init__(self, *, base_url: str, timeout: float) -> None:
            self.base_url = base_url
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, path: str, json: dict[str, object]) -> DummyResponse:
            assert path == "/api/embed"
            assert json == {
                "model": "embeddinggemma",
                "input": "policy",
            }
            return DummyResponse()

    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)

    provider = OllamaEmbeddingProvider(base_url="http://localhost:11434", timeout=10.0)
    embedding = anyio.run(lambda: provider.embed(text="policy", model="embeddinggemma"))

    assert embedding == [0.1, 0.2, 0.3]
