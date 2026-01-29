from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import configure_logging, request_id_middleware
from app.api.wise import router as wise_router
from app.api.webhooks import router as webhooks_router

configure_logging()

app = FastAPI(title="AI CFO Wise API")

cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"] if settings.environment == "local" else ["GET", "POST"],
    allow_headers=["*"] if settings.environment == "local" else ["Authorization", "Content-Type"],
)

app.middleware("http")(request_id_middleware)

app.include_router(wise_router)
app.include_router(webhooks_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return {"app": f"{settings.app_name}-wise", "environment": settings.environment}
