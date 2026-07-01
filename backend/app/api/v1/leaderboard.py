from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_leaderboard_service
from app.models.schemas import LeaderboardResponse, LeaderboardSubmitRequest
from app.services.leaderboard import LeaderboardService
from app.services.result import LeaderboardNotEligibleError, ResultNotFoundError

router = APIRouter(prefix="/leaderboard")


@router.post("", status_code=204)
async def submit_leaderboard(
    body: LeaderboardSubmitRequest,
    service: LeaderboardService = Depends(get_leaderboard_service),
) -> None:
    try:
        await service.submit(body.player_name, body.score, body.session_id)
    except ResultNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result not found: {exc.session_id}",
        ) from exc
    except LeaderboardNotEligibleError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Leaderboard submission not allowed for completion_type="
                f"{exc.completion_type}"
            ),
        ) from exc


@router.get("", response_model=LeaderboardResponse)
async def get_leaderboard(
    service: LeaderboardService = Depends(get_leaderboard_service),
) -> LeaderboardResponse:
    entries = await service.top(100)
    return LeaderboardResponse(entries=entries)
