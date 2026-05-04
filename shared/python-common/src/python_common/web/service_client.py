from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx
from pydantic import BaseModel

from python_common import UpstreamServiceError
from python_common.logging_utils import get_logger

logger = get_logger(__name__)


async def post_json(
    *,
    service: str,
    base_url: str,
    path: str,
    payload: Mapping[str, Any],
    headers: Mapping[str, str],
    timeout: float,
    retry_count: int,
) -> dict[str, Any]:
    attempts = retry_count + 1

    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
                response = await client.post(path, json=dict(payload), headers=dict(headers))
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise UpstreamServiceError(
                service=service,
                status_code=exc.response.status_code,
                message=f"{service} returned an error",
                details={
                    "path": path,
                    "response_text": exc.response.text,
                },
            ) from exc
        except httpx.HTTPError as exc:
            if attempt == attempts:
                raise UpstreamServiceError(
                    service=service,
                    message=f"{service} is unavailable",
                    details={"path": path, "attempts": attempt},
                ) from exc

            logger.warning(
                "upstream_retry service=%s path=%s attempt=%s",
                service,
                path,
                attempt,
            )

    raise UpstreamServiceError(
        service=service,
        message=f"{service} is unavailable",
        details={"path": path, "attempts": attempts},
    )


async def post_json_model(
    *,
    service: str,
    base_url: str,
    path: str,
    payload: BaseModel,
    headers: Mapping[str, str],
    timeout: float,
    retry_count: int,
    response_model: type[BaseModel],
) -> BaseModel:
    response_json = await post_json(
        service=service,
        base_url=base_url,
        path=path,
        payload=payload.model_dump(exclude_none=True),
        headers=headers,
        timeout=timeout,
        retry_count=retry_count,
    )
    return response_model.model_validate(response_json)
