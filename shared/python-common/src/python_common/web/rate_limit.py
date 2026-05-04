"""Rate limiting middleware using slowapi."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def _key_func(request: Request) -> str:
    """Rate limit by tenant_id if present, otherwise by IP."""
    tenant = request.headers.get("x-tenant-id")
    if tenant and tenant != "default":
        return f"tenant:{tenant}"
    return get_remote_address(request)


def setup_rate_limiting(app: FastAPI, *, rate_limit_per_minute: int) -> None:
    """Add rate limiting to a FastAPI application.

    Args:
        app: The FastAPI application instance.
        rate_limit_per_minute: Maximum requests per minute per key.
    """
    if rate_limit_per_minute <= 0:
        return

    limiter = Limiter(key_func=_key_func, default_limits=[f"{rate_limit_per_minute}/minute"])
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded: {exc.detail}",
                    "details": {"limit": str(rate_limit_per_minute)},
                }
            },
            headers={"Retry-After": str(60)},
        )

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        # Skip rate limiting for health and metrics endpoints
        if request.url.path in ("/health", "/metrics"):
            return await call_next(request)

        response = await call_next(request)
        return response
