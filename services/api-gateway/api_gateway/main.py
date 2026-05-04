from python_common import AppSettings
from python_common.web import create_service_app

from api_gateway.routes import build_router

settings = AppSettings(service_name="api-gateway")
app = create_service_app(title="API Gateway", version="0.1.0", settings=settings)
app.include_router(build_router(settings))
