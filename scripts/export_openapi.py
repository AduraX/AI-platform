#!/usr/bin/env python3
"""Export OpenAPI specs for all FastAPI services.

Usage:
    uv run python scripts/export_openapi.py

Outputs JSON files to docs/api/openapi/
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

SERVICES = {
    "api-gateway": "api_gateway.main:app",
    "chat-service": "chat_service.main:app",
    "rag-service": "rag_service.main:app",
    "ingestion-service": "ingestion_service.main:app",
    "ocr-service": "ocr_service.main:app",
    "model-router": "model_router.main:app",
    "eval-service": "eval_service.main:app",
}

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "api" / "openapi"


def export_all() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for service_name, app_path in SERVICES.items():
        module_path, attr = app_path.split(":")
        try:
            # Add service path for imports
            service_dir = (
                Path(__file__).resolve().parents[1] / "services" / service_name
            )
            if str(service_dir) not in sys.path:
                sys.path.insert(0, str(service_dir))

            module = importlib.import_module(module_path)
            app = getattr(module, attr)
            schema = app.openapi()

            output_file = OUTPUT_DIR / f"{service_name}.json"
            output_file.write_text(json.dumps(schema, indent=2) + "\n")
            print(f"Exported {service_name} -> {output_file}")

        except Exception as e:
            print(f"Failed to export {service_name}: {e}", file=sys.stderr)


if __name__ == "__main__":
    export_all()
