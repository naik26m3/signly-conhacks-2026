from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from config.settings import settings
from config.database import Database
from config.redis import RedisClient
from config.gemini import GeminiClient
from config.elevenlabs import ElevenLabsClient
from config.langfuse import LangfuseClient
from middleware.request_logger import log_requests
from models.handTracking import HandTracker
from routers import health, sign, speech, uploads
from services.inference import InferenceService
from services.speech import SpeechService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Infrastructure
    await Database.connect()
    await RedisClient.connect()
    HandTracker.load()
    # AI clients (created in config, passed to services)
    gemini = GeminiClient.connect()
    elevenlabs = ElevenLabsClient.connect()
    langfuse = LangfuseClient.connect()
    # Service instances wired with their clients
    app.state.inference = InferenceService(gemini=gemini, langfuse=langfuse)
    app.state.speech = SpeechService(elevenlabs=elevenlabs)
    yield
    HandTracker.unload()
    await Database.disconnect()
    await RedisClient.disconnect()


app = FastAPI(
    title="Sign Bridge API",
    version=settings.api_version,
    description="Real-time sign language ↔ spoken language communication backend",
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.middleware("http")(log_requests)

app.include_router(health.router)
app.include_router(sign.router)
app.include_router(speech.router)
app.include_router(uploads.router)
