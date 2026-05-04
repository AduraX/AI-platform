from __future__ import annotations

from typing import Protocol

import httpx
from python_common import AppSettings, UpstreamServiceError


class EmbeddingProvider(Protocol):
    async def embed(self, *, text: str, model: str) -> list[float]:
        """Return one embedding vector for the supplied text."""


class DeterministicEmbeddingProvider:
    def __init__(self, *, dimensions: int = 8) -> None:
        self.dimensions = dimensions

    async def embed(self, *, text: str, model: str) -> list[float]:
        _ = model
        values = [0.0 for _ in range(self.dimensions)]
        for index, byte in enumerate(text.encode("utf-8")):
            values[index % self.dimensions] += byte / 255.0

        magnitude = sum(value * value for value in values) ** 0.5
        if magnitude == 0:
            return values

        return [round(value / magnitude, 6) for value in values]


class OllamaEmbeddingProvider:
    def __init__(self, *, base_url: str, timeout: float) -> None:
        self.base_url = base_url
        self.timeout = timeout

    async def embed(self, *, text: str, model: str) -> list[float]:
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
                response = await client.post(
                    "/api/embed",
                    json={
                        "model": model,
                        "input": text,
                    },
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise UpstreamServiceError(
                service="ollama",
                status_code=exc.response.status_code,
                message="ollama returned an error while generating embeddings",
                details={
                    "path": "/api/embed",
                    "response_text": exc.response.text,
                },
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamServiceError(
                service="ollama",
                message="ollama is unavailable while generating embeddings",
                details={"path": "/api/embed"},
            ) from exc

        payload = response.json()
        embeddings = payload.get("embeddings")
        if not isinstance(embeddings, list) or not embeddings:
            raise UpstreamServiceError(
                service="ollama",
                message="ollama returned an invalid embedding response",
                details={"path": "/api/embed"},
            )

        embedding = embeddings[0]
        if not isinstance(embedding, list) or not all(
            isinstance(value, int | float) for value in embedding
        ):
            raise UpstreamServiceError(
                service="ollama",
                message="ollama returned an invalid embedding vector",
                details={"path": "/api/embed"},
            )

        return [float(value) for value in embedding]


def create_embedding_provider(settings: AppSettings) -> EmbeddingProvider:
    if settings.embedding_provider == "deterministic":
        return DeterministicEmbeddingProvider()

    return OllamaEmbeddingProvider(
        base_url=settings.ollama_base_url,
        timeout=settings.request_timeout_seconds,
    )
