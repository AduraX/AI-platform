from pydantic import BaseModel, Field


class RequestContext(BaseModel):
    tenant_id: str = Field(default="default")
    user_id: str = Field(default="anonymous")
    roles: list[str] = Field(default_factory=list)
    request_id: str = Field(default="unknown")
