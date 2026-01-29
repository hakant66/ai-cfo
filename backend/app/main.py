from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import configure_logging, request_id_middleware
from app.api.auth import router as auth_router
from app.api.companies import router as companies_router
from app.api.connectors import router as connectors_router
from app.api.imports import router as imports_router
from app.api.metrics import router as metrics_router
from app.api.demo_data import router as demo_data_router
from app.api.dify_tools import router as dify_tools_router
from app.api.alerts import router as alerts_router
from app.api.chat import router as chat_router
from app.api.payables import router as payables_router
from app.api.exchange_rates import router as exchange_rates_router
from app.api.knowledge import router as knowledge_router

configure_logging()

app = FastAPI(title="AI CFO API")


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version="0.1.0",
        routes=app.routes,
    )
    schema["servers"] = [
        {"url": "http://localhost:8000"},
        {"url": "http://127.0.0.1:8000"},
        {"url": "http://host.docker.internal:8000"},
        {"url": "http://backend:8000"},
    ]
    app.openapi_schema = schema
    return app.openapi_schema


app.openapi = custom_openapi

cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"] if settings.environment == "local" else ["GET", "POST"],
    allow_headers=["*"] if settings.environment == "local" else ["Authorization", "Content-Type"],
)

app.middleware("http")(request_id_middleware)

app.include_router(auth_router)
app.include_router(companies_router)
app.include_router(connectors_router)
app.include_router(imports_router)
app.include_router(metrics_router)
app.include_router(demo_data_router)
app.include_router(dify_tools_router)
app.include_router(alerts_router)
app.include_router(chat_router)
app.include_router(payables_router)
app.include_router(exchange_rates_router)
app.include_router(knowledge_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return {"app": settings.app_name, "environment": settings.environment}
