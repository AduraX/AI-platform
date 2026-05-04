from python_common import AppSettings
from python_common.web import create_service_app

from model_router.routes import build_router

settings = AppSettings(service_name="model-router")
app = create_service_app(title="Model Router", version="0.1.0", settings=settings)
app.include_router(build_router(settings))
