"""OpenTelemetry distributed tracing for the enterprise AI platform."""
from __future__ import annotations

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


def setup_tracing(
    *,
    service_name: str,
    environment: str = "development",
    otlp_endpoint: str | None = None,
) -> trace.Tracer:
    """Initialize OpenTelemetry tracing for a service.

    Args:
        service_name: Name of the service (used in spans).
        environment: Deployment environment label.
        otlp_endpoint: OTLP collector endpoint. If None, uses console exporter.

    Returns:
        A configured Tracer instance.
    """
    resource = Resource.create({
        "service.name": service_name,
        "deployment.environment": environment,
    })

    provider = TracerProvider(resource=resource)

    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)

    # Auto-instrument httpx for outbound call tracing
    HTTPXClientInstrumentor().instrument()

    return trace.get_tracer(service_name)


def instrument_app(app: object) -> None:
    """Instrument a FastAPI app for automatic span creation on requests."""
    FastAPIInstrumentor.instrument_app(app)  # type: ignore[arg-type]


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer for manual span creation."""
    return trace.get_tracer(name)
