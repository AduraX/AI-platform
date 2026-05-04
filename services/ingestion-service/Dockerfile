FROM python:3.11-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.13 /uv /uvx /bin/
WORKDIR /workspace
ENV UV_LINK_MODE=copy
COPY shared/python-common /workspace/shared/python-common
COPY services/ingestion-service /workspace/services/ingestion-service
RUN uv pip install --system --no-cache -e /workspace/shared/python-common -e /workspace/services/ingestion-service
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser && \
    chown -R appuser:appgroup /workspace
EXPOSE 8004
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8004/health')"]
WORKDIR /workspace/services/ingestion-service
USER appuser
CMD ["uvicorn", "ingestion_service.main:app", "--host", "0.0.0.0", "--port", "8004"]
