from contextlib import asynccontextmanager
from typing import AsyncIterator

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import configure_logging, logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    app.state.redis = redis_client
    logger.info("backend_started", redis_url=settings.redis_url, ollama_host=settings.ollama_host)
    try:
        yield
    finally:
        await redis_client.aclose()
        logger.info("backend_stopped")


app = FastAPI(
    title="Token Trail API",
    description="Visualizing LLM Decoding Through Interactive Gameplay",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str | bool]:
    redis_ok = False
    try:
        redis_client: redis.Redis = app.state.redis
        redis_ok = await redis_client.ping()
    except Exception:
        redis_ok = False

    status = "ok" if redis_ok else "degraded"
    return {
        "status": status,
        "service": "token-trail-api",
        "redis": redis_ok,
    }
