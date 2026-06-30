from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import get_game_step_service, get_trace_id
from app.models.schemas import StepRequest, StepResponse
from app.services.game_step import GameStepService, InvalidTokenError, SessionNotFoundError

router = APIRouter(prefix="/game")


@router.post("/step", response_model=StepResponse)
async def game_step(
    body: StepRequest,
    request: Request,
    response: Response,
    service: GameStepService = Depends(get_game_step_service),
) -> StepResponse:
    trace_id = get_trace_id(request)
    try:
        step_response, profile = await service.execute(
            session_id=body.session_id,
            eaten_token_id=body.eaten_token_id,
            current_snake_length=body.current_snake_length,
            trace_id=trace_id,
        )
        response.headers["X-Step-Profile"] = profile.as_header_value()
        return step_response
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {exc.session_id}",
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid token: {exc.token_id}",
        ) from exc
