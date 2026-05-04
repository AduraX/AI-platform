from python_common import AppSettings
from python_common.web import create_service_app

from chat_service.routes import build_router

settings = AppSettings(service_name="chat-service")
app = create_service_app(title="Chat Service", version="0.1.0", settings=settings)
app.include_router(build_router(settings))
