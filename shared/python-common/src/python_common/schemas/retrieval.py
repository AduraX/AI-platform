from pydantic import BaseModel, Field


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1)
    tenant_id: str = "default"
    query_embedding: list[float] | None = None
    top_k: int | None = Field(default=None, ge=1, le=50)


class RetrievalContext(BaseModel):
    chunk_id: str
    content: str
    score: float
    source: str


class PaginationMeta(BaseModel):
    total: int
    offset: int = 0
    limit: int


class RetrieveResponse(BaseModel):
    service: str
    query: str
    contexts: list[RetrievalContext]
    pagination: PaginationMeta | None = None


class VectorIndexChunk(BaseModel):
    chunk_id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source: str = Field(min_length=1)
    embedding: list[float] = Field(min_length=1)


class VectorIndexRequest(BaseModel):
    document_id: str = Field(min_length=1)
    chunks: list[VectorIndexChunk] = Field(min_length=1)


class VectorIndexResponse(BaseModel):
    service: str
    document_id: str
    indexed_count: int
