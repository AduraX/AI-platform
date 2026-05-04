from pydantic import BaseModel, Field


class EvalRequest(BaseModel):
    suite_name: str = Field(min_length=1)


class EvalCreatedResponse(BaseModel):
    service: str
    suite_name: str

