import uuid
from typing import cast

from fastapi import Request
from redis.asyncio import Redis

from app.cache.branch_cache import BranchCache
from app.core.config import settings
from app.services.fallback import FallbackService
from app.services.game_step import GameStepService
from app.services.leaderboard import LeaderboardService
from app.services.prefetcher import PrefetchScheduler
from app.services.session import SessionManager


def get_redis(request: Request) -> Redis:
    return cast(Redis, request.app.state.redis)


def get_trace_id(request: Request) -> str:
    return getattr(request.state, "trace_id", str(uuid.uuid4()))


def build_game_step_service(redis: Redis) -> GameStepService:
    cache = BranchCache(redis)
    return GameStepService(
        sessions=SessionManager(redis),
        cache=cache,
        fallback=FallbackService(),
        prefetcher=PrefetchScheduler(cache, enabled=settings.prefetch_enabled),
    )


def get_game_step_service(request: Request) -> GameStepService:
    service = getattr(request.app.state, "game_step_service", None)
    if service is None:
        return build_game_step_service(get_redis(request))
    return cast(GameStepService, service)


def get_session_manager(redis: Redis) -> SessionManager:
    return SessionManager(redis)


def get_branch_cache(redis: Redis) -> BranchCache:
    return BranchCache(redis)


def get_leaderboard_service(redis: Redis) -> LeaderboardService:
    return LeaderboardService(redis)
