from fastapi import APIRouter, Depends
from redis.asyncio import Redis

from app.api.deps import get_leaderboard_service, get_redis
from app.models.schemas import LeaderboardResponse, LeaderboardSubmitRequest
from app.services.leaderboard import LeaderboardService

router = APIRouter(prefix="/leaderboard")


@router.post("", status_code=204)
async def submit_leaderboard(
    body: LeaderboardSubmitRequest,
    redis: Redis = Depends(get_redis),
) -> None:
    service = get_leaderboard_service(redis)
    await service.submit(body.player_name, body.score, body.session_id)


@router.get("", response_model=LeaderboardResponse)
async def get_leaderboard(
    redis: Redis = Depends(get_redis),
) -> LeaderboardResponse:
    service: LeaderboardService = get_leaderboard_service(redis)
    entries = await service.top(100)
    return LeaderboardResponse(entries=entries)
