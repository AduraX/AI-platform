"""Prometheus metrics for FastAPI services."""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse


class MetricsCollector:
    """Simple Prometheus-compatible metrics collector."""

    def __init__(self, service_name: str) -> None:
        self.service_name = service_name
        self._prefix = service_name.replace("-", "_")
        self._request_count: dict[str, int] = defaultdict(int)
        self._request_duration_sum: dict[str, float] = defaultdict(float)
        self._request_duration_count: dict[str, int] = defaultdict(int)
        self._error_count: dict[str, int] = defaultdict(int)

    def record_request(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        key = f'{method}|{path}|{status_code}'
        self._request_count[key] += 1
        self._request_duration_sum[key] += duration_seconds
        self._request_duration_count[key] += 1
        if status_code >= 400:
            error_key = f'{method}|{path}|{status_code}'
            self._error_count[error_key] += 1

    def render(self) -> str:
        lines: list[str] = []
        p = self._prefix

        lines.append(f"# HELP {p}_http_requests_total Total HTTP requests")
        lines.append(f"# TYPE {p}_http_requests_total counter")
        for key, count in self._request_count.items():
            method, path, status = key.split("|")
            labels = f'method="{method}",path="{path}",status="{status}"'
            lines.append(f"{p}_http_requests_total{{{labels}}} {count}")

        lines.append(f"# HELP {p}_http_request_duration_seconds HTTP request duration")
        lines.append(f"# TYPE {p}_http_request_duration_seconds summary")
        for key, total in self._request_duration_sum.items():
            method, path, status = key.split("|")
            count = self._request_duration_count[key]
            labels = f'method="{method}",path="{path}",status="{status}"'
            lines.append(f"{p}_http_request_duration_seconds_sum{{{labels}}} {total:.6f}")
            lines.append(f"{p}_http_request_duration_seconds_count{{{labels}}} {count}")

        return "\n".join(lines) + "\n"


def create_metrics_router(collector: MetricsCollector) -> APIRouter:
    router = APIRouter()

    @router.get("/metrics", response_class=PlainTextResponse, tags=["system"])
    def metrics() -> str:
        return collector.render()

    return router
