from pydantic import BaseModel, Field

from python_common.schemas.common import AcceptedResponse


class GenerationRequest(BaseModel):
    prompt: str = Field(min_length=1)
    model: str | None = None


class GenerationAcceptedResponse(AcceptedResponse):
    model: str


class EmbeddingRequest(BaseModel):
    input: str = Field(min_length=1)
    model: str | None = None


class EmbeddingResponse(BaseModel):
    service: str
    model: str
    embedding: list[float]
