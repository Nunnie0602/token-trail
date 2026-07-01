from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.deps import (
    get_finalize_service,
    get_game_step_service,
    get_result_manager,
    get_trace_id,
)
from app.models.schemas import FinalizeRequest, GameResult, StepRequest, StepResponse
from app.services.game_step import GameStepService, InvalidTokenError, SessionNotFoundError
from app.services.result import (
    FinalizeService,
    InvalidFinalizeStateError,
    ResultManager,
    ResultNotFoundError,
)

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


@router.post(
    "/finalize",
    response_model=GameResult,
    status_code=status.HTTP_201_CREATED,
    responses={204: {"description": "Session discarded (snake_length < 3 voluntary exit)"}},
)
async def finalize_game(
    body: FinalizeRequest,
    service: FinalizeService = Depends(get_finalize_service),
) -> GameResult | Response:
    try:
        result = await service.finalize(
            session_id=body.session_id,
            completion_type=body.completion_type,
            failure_reason=body.failure_reason,
        )
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {exc.session_id}",
        ) from exc
    except InvalidFinalizeStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot finalize session in state {exc.game_status}",
        ) from exc

    if result is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return result


@router.get("/result/{session_id}", response_model=GameResult)
async def get_game_result(
    session_id: str,
    results: ResultManager = Depends(get_result_manager),
) -> GameResult:
    result = await results.get(session_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result not found: {session_id}",
        ) from ResultNotFoundError(session_id)
    return result
