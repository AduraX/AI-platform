from pydantic import BaseModel, Field


class IngestionJobResponse(BaseModel):
    service: str
    job_id: str
    document_id: str
    status: str
    indexed_chunks: int = 0
    error: str | None = None


class DocumentRequest(BaseModel):
    filename: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    text: str | None = Field(default=None, min_length=1)


class DocumentCreatedResponse(BaseModel):
    service: str
    document_id: str
    filename: str
    job_id: str
    status: str
    indexed_chunks: int = 0
    object_key: str | None = None
    upload_url: str | None = None


class OcrRequest(BaseModel):
    document_id: str = Field(min_length=1)
    object_key: str = Field(min_length=1)


class OcrResponse(BaseModel):
    service: str = "ocr-service"
    status: str
    document_id: str
    object_key: str
    extracted_text: str
    content_type: str | None = None
    page_count: int | None = None
    tables: list[str] = []
