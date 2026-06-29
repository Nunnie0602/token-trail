from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, logger
from app.core.middleware import TraceIdMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    redis_client: redis.Redis = redis.from_url(settings.redis_url, decode_responses=True)  # type: ignore[no-untyped-call]
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
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(TraceIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


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
