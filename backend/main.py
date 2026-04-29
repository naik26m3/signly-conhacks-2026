import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from middleware.request_logger import log_requests
from routers import health, sign, speech, uploads

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

app = FastAPI(
    title="Sign Bridge API",
    version=settings.api_version,
    description="Real-time sign language ↔ spoken language communication backend",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.middleware("http")(log_requests)

app.include_router(health.router)
app.include_router(sign.router)
app.include_router(speech.router)
app.include_router(uploads.router)
