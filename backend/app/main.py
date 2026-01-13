import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import alerts, auth, chat, companies, connectors, health, imports, metrics
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aicfo")

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info("request_completed", extra={"path": request.url.path, "request_id": request_id})
    return response


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(connectors.router)
app.include_router(imports.router)
app.include_router(metrics.router)
app.include_router(alerts.router)
app.include_router(chat.router)
