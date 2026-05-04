from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    service: str
    status: str = "ok"
    environment: str = Field(default="development")
    checks: dict[str, str] = Field(default_factory=dict)


class AcceptedResponse(BaseModel):
    service: str
    status: str = "accepted"

