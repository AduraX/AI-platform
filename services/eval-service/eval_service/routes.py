from fastapi import APIRouter
from python_common.schemas import EvalCreatedResponse, EvalRequest

router = APIRouter(tags=["evaluation"])


@router.post("/v1/evals", response_model=EvalCreatedResponse)
def create_eval(payload: EvalRequest) -> EvalCreatedResponse:
    return EvalCreatedResponse(service="eval-service", suite_name=payload.suite_name)
