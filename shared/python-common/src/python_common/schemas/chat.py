from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    service: str
    reply: str
    sources: list[str] = Field(default_factory=list)


class ChatStreamEvent(BaseModel):
    """A single event in a streaming chat response."""
    event: str = Field(description="Event type: token, source, done, error")
    data: str = Field(default="")


class ChatStreamRequest(BaseModel):
    message: str = Field(min_length=1)
    stream: bool = Field(default=True)
