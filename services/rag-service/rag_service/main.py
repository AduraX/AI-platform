from python_common import AppSettings
from python_common.web import create_service_app

from rag_service.routes import create_retrieval_router
from rag_service.vector_store import create_vector_store

settings = AppSettings(service_name="rag-service")
vector_store = create_vector_store(settings)
app = create_service_app(title="RAG Service", version="0.1.0", settings=settings)
app.include_router(create_retrieval_router(vector_store, default_top_k=settings.retrieval_top_k))
