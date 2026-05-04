from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from python_common.web import health_response


def load_module():
    module_path = Path(__file__).resolve().parents[1] / "ocr_service" / "main.py"
    spec = spec_from_file_location("ocr_service_main", module_path)
    module = module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_health() -> None:
    module = load_module()
    response = health_response(module.settings)

    assert response.service == "ocr-service"
    assert response.status == "ok"
    assert any(route.path == "/health" for route in module.app.routes)
    assert any(route.path == "/internal/ocr" for route in module.app.routes)
