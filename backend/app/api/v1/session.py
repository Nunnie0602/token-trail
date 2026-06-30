from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis

from app.api.deps import get_redis, get_session_manager
from app.cache.branch_cache import BranchCache
from app.models.schemas import CreateSessionRequest, CreateSessionResponse, SessionResponse
from app.services.prefetcher import PrefetchScheduler
from app.services.session import SessionManager

router = APIRouter(prefix="/session")


@router.post("", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionRequest,
    redis: Redis = Depends(get_redis),
) -> CreateSessionResponse:
    sessions = get_session_manager(redis)
    session = await sessions.create(body.mode, body.model)
    next_tokens = sessions.initial_next_tokens(session)

    cache = BranchCache(redis)
    prefetcher = PrefetchScheduler(cache)
    if next_tokens:
        await prefetcher.seed_branches(
            session_id=session.session_id,
            mode=session.mode,
            model=session.model,
            branch_token_ids=[token.token_id for token in next_tokens if not token.is_eos],
        )

    return CreateSessionResponse(
        session_id=session.session_id,
        mode=session.mode,
        model=session.model,
        game_status=session.game_status,
        current_prompt=session.current_prompt,
        current_temperature=session.current_temperature,
        snake_length=session.snake_length,
        current_node_id=session.current_node_id or "",
        next_tokens_food=next_tokens,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    redis: Redis = Depends(get_redis),
) -> SessionResponse:
    sessions: SessionManager = get_session_manager(redis)
    session = await sessions.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    return SessionResponse(
        session_id=session.session_id,
        mode=session.mode,
        model=session.model,
        game_status=session.game_status,
        current_prompt=session.current_prompt,
        current_temperature=session.current_temperature,
        snake_length=session.snake_length,
        current_node_id=session.current_node_id,
        updated_at=datetime.fromisoformat(session.updated_at),
    )
