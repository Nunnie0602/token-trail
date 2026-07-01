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
from app.services.result import FinalizeService, ResultManager
from app.services.session import SessionManager


def get_redis(request: Request) -> Redis:
    return cast(Redis, request.app.state.redis)


def get_trace_id(request: Request) -> str:
    return getattr(request.state, "trace_id", str(uuid.uuid4()))


def build_result_manager(redis: Redis) -> ResultManager:
    return ResultManager(redis)


def build_finalize_service(redis: Redis) -> FinalizeService:
    sessions = SessionManager(redis)
    results = ResultManager(redis)
    return FinalizeService(sessions, results)


def build_game_step_service(redis: Redis) -> GameStepService:
    cache = BranchCache(redis)
    sessions = SessionManager(redis)
    results = ResultManager(redis)
    finalize = FinalizeService(sessions, results)
    return GameStepService(
        sessions=sessions,
        cache=cache,
        fallback=FallbackService(),
        prefetcher=PrefetchScheduler(cache, enabled=settings.prefetch_enabled),
        finalize=finalize,
    )


def get_game_step_service(request: Request) -> GameStepService:
    service = getattr(request.app.state, "game_step_service", None)
    if service is None:
        return build_game_step_service(get_redis(request))
    return cast(GameStepService, service)


def get_session_manager(redis: Redis) -> SessionManager:
    return SessionManager(redis)


def get_result_manager_from_redis(redis: Redis) -> ResultManager:
    return ResultManager(redis)


def get_finalize_service_from_redis(redis: Redis) -> FinalizeService:
    sessions = SessionManager(redis)
    return FinalizeService(sessions, ResultManager(redis))


def get_result_manager(request: Request) -> ResultManager:
    return ResultManager(get_redis(request))


def get_finalize_service(request: Request) -> FinalizeService:
    redis = get_redis(request)
    return FinalizeService(SessionManager(redis), ResultManager(redis))


def get_leaderboard_service_from_redis(redis: Redis) -> LeaderboardService:
    return LeaderboardService(redis, ResultManager(redis))


def get_leaderboard_service(request: Request) -> LeaderboardService:
    redis = get_redis(request)
    return LeaderboardService(redis, ResultManager(redis))
