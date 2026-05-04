FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.9.13 /uv /uvx /bin/
WORKDIR /workspace
ENV UV_LINK_MODE=copy
COPY shared/python-common /workspace/shared/python-common
COPY services/ocr-service /workspace/services/ocr-service
RUN uv pip install --system --no-cache -e /workspace/shared/python-common -e /workspace/services/ocr-service
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup appuser && \
    chown -R appuser:appgroup /workspace
EXPOSE 8005
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8005/health')"]
WORKDIR /workspace/services/ocr-service
USER appuser
CMD ["uvicorn", "ocr_service.main:app", "--host", "0.0.0.0", "--port", "8005"]
