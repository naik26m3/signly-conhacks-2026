from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from config.database import Database
from config.redis import RedisClient
from middleware.request_logger import log_requests
from routers import health, sign, speech, uploads

@asynccontextmanager
async def lifespan(app: FastAPI):
    await Database.connect()
    await RedisClient.connect()
    yield
    await Database.disconnect()
    await RedisClient.disconnect()

app = FastAPI(
    title="Sign Bridge API",
    version=settings.api_version,
    description="Real-time sign language ↔ spoken language communication backend",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.middleware("http")(log_requests)

app.include_router(health.router)
app.include_router(sign.router)
app.include_router(speech.router)
app.include_router(uploads.router)
