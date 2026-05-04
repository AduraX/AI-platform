"""Observability utilities for the enterprise AI platform."""
from python_common.observability.metrics import MetricsCollector, create_metrics_router
from python_common.observability.tracing import get_tracer, instrument_app, setup_tracing


def metric_prefix(service_name: str) -> str:
    return service_name.replace("-", "_")


__all__ = [
    "MetricsCollector",
    "create_metrics_router",
    "get_tracer",
    "instrument_app",
    "metric_prefix",
    "setup_tracing",
]
