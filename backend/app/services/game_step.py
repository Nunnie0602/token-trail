from app.cache.branch_cache import BranchCache
from app.core.logging import logger
from app.models.schemas import StepResponse
from app.services.corpus import find_token
from app.services.fallback import FallbackService
from app.services.prefetcher import PrefetchScheduler
from app.services.session import SessionManager
from app.services.temperature import derive_speed_multiplier, derive_temperature


class GameStepService:
    def __init__(
        self,
        sessions: SessionManager,
        cache: BranchCache,
        fallback: FallbackService,
        prefetcher: PrefetchScheduler,
    ) -> None:
        self._sessions = sessions
        self._cache = cache
        self._fallback = fallback
        self._prefetcher = prefetcher

    async def execute(
        self,
        *,
        session_id: str,
        eaten_token_id: str,
        current_snake_length: int,
        trace_id: str,
    ) -> StepResponse:
        session = await self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)

        eaten_token = find_token(session.mode, session.model, eaten_token_id)
        if eaten_token is None:
            raise InvalidTokenError(eaten_token_id)

        cached = await self._cache.get(session_id, eaten_token_id)
        cache_hit = cached is not None

        if cache_hit:
            next_tokens = cached
            logger.info(
                "step_cache_hit",
                session_id=session_id,
                trace_id=trace_id,
                eaten_token_id=eaten_token_id,
            )
        else:
            next_tokens = await self._fallback.resolve(
                session_id=session_id,
                trace_id=trace_id,
                mode=session.mode,
                model=session.model,
                eaten_token_id=eaten_token_id,
            )
            logger.info(
                "step_cache_miss",
                session_id=session_id,
                trace_id=trace_id,
                eaten_token_id=eaten_token_id,
            )

        is_eos = eaten_token.is_eos
        temperature = derive_temperature(eaten_token.prob)
        session.current_prompt = f"{session.current_prompt}{eaten_token.text}"
        session.snake_length = current_snake_length
        session.current_temperature = temperature
        session.current_node_id = eaten_token_id
        session.score += round(eaten_token.prob * 100)

        if is_eos:
            session.game_status = "ENDED"
            next_tokens = []
        else:
            session.game_status = "PLAYING"

        await self._sessions.save(session)

        if not is_eos and next_tokens:
            branch_ids = [token.token_id for token in next_tokens if not token.is_eos]
            await self._prefetcher.schedule(
                session_id=session_id,
                trace_id=trace_id,
                mode=session.mode,
                model=session.model,
                branch_token_ids=branch_ids,
            )

        return StepResponse(
            session_id=session_id,
            game_status=session.game_status,
            current_temperature=temperature,
            snake_speed_multiplier=derive_speed_multiplier(temperature),
            next_tokens_food=next_tokens or [],
            cache_hit=cache_hit,
        )

class SessionNotFoundError(Exception):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Session not found: {session_id}")


class InvalidTokenError(Exception):
    def __init__(self, token_id: str) -> None:
        self.token_id = token_id
        super().__init__(f"Invalid token: {token_id}")
