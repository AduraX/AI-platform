import time
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from python_common.config.settings import AppSettings
from python_common.errors import PlatformError
from python_common.logging_utils import configure_logging, get_logger
from python_common.observability import MetricsCollector, create_metrics_router
from python_common.schemas import ErrorBody, ErrorResponse, HealthResponse
from python_common.schemas.auth import RequestContext
from python_common.web.context import request_context_from_headers, request_context_to_headers
from python_common.web.jwt_auth import validate_jwt_token

logger = get_logger(__name__)


def health_response(settings: AppSettings) -> HealthResponse:
    return HealthResponse(
        service=settings.service_name,
        environment=settings.environment,
    )


def create_service_app(*, title: str, version: str, settings: AppSettings) -> FastAPI:
    configure_logging(settings.log_level)

    app = FastAPI(title=title, version=version)

    if settings.tracing_enabled:
        from python_common.observability import instrument_app, setup_tracing
        setup_tracing(
            service_name=settings.service_name,
            environment=settings.environment,
            otlp_endpoint=settings.otlp_endpoint,
        )
        instrument_app(app)

    collector = MetricsCollector(settings.service_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from python_common.web.rate_limit import setup_rate_limiting
    setup_rate_limiting(app, rate_limit_per_minute=settings.rate_limit_per_minute)

    router = APIRouter()

    @app.middleware("http")
    async def security_headers_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not request.url.path.rstrip("/").endswith("/health"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.middleware("http")
    async def request_context_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        context = request_context_from_headers(request)
        request.state.request_context = context
        request.state.request_started_at = time.perf_counter()

        if settings.auth_enabled:
            claims = await validate_jwt_token(request, settings)
            if claims:
                context = RequestContext(
                    tenant_id=claims.get("tenant_id", context.tenant_id),
                    user_id=claims.get("email", context.user_id),
                    roles=claims.get("realm_access", {}).get("roles", context.roles),
                    request_id=context.request_id,
                )
                request.state.request_context = context

        response = await call_next(request)
        response.headers.update(request_context_to_headers(context))

        duration_ms = round((time.perf_counter() - request.state.request_started_at) * 1000, 2)
        collector.record_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_seconds=(time.perf_counter() - request.state.request_started_at),
        )
        logger.info(
            "request service=%s method=%s path=%s status=%s"
            " tenant_id=%s user_id=%s request_id=%s duration_ms=%s",
            settings.service_name,
            request.method,
            request.url.path,
            response.status_code,
            context.tenant_id,
            context.user_id,
            context.request_id,
            duration_ms,
        )
        return response

    @app.exception_handler(PlatformError)
    async def handle_platform_error(
        request: Request,
        exc: PlatformError,
    ) -> JSONResponse:
        _ = request
        payload = ErrorResponse(
            error=ErrorBody(
                code=exc.code,
                message=exc.message,
                details={
                    **exc.details,
                    "request_id": request_context_from_headers(request).request_id,
                },
            )
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @router.get("/health", response_model=HealthResponse, tags=["system"])
    def health() -> HealthResponse:
        return health_response(settings)

    app.include_router(router)
    app.include_router(create_metrics_router(collector))
    return app
