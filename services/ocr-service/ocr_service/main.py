from python_common import AppSettings
from python_common.web import create_service_app

from ocr_service.routes import router

settings = AppSettings(service_name="ocr-service")
app = create_service_app(title="OCR Service", version="0.1.0", settings=settings)
app.include_router(router)
