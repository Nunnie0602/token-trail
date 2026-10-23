import time

from app.cache.branch_cache import BranchCache
from app.core.config import settings
from app.core.logging import logger
from app.core.step_profile import StepProfile
from app.models.schemas import StepRecord, StepResponse
from app.services.decoding import (
    derive_speed_multiplier,
    derive_temperature,
    initial_prompt_segment,
    rebuild_sliding_prompt,
)
from app.services.fallback import FallbackService
from app.services.prefetcher import PrefetchScheduler
from app.services.result import FinalizeService
from app.services.session import SessionManager
from app.services.token_resolver import register_dynamic_tokens, resolve_token


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000


class GameStepService:
    def __init__(
        self,
        sessions: SessionManager,
        cache: BranchCache,
        fallback: FallbackService,
        prefetcher: PrefetchScheduler,
        finalize: FinalizeService | None = None,
    ) -> None:
        self._sessions = sessions
        self._cache = cache
        self._fallback = fallback
        self._prefetcher = prefetcher
        self._finalize = finalize

    async def execute(
        self,
        *,
        session_id: str,
        eaten_token_id: str,
        current_snake_length: int,
        trace_id: str,
    ) -> tuple[StepResponse, StepProfile]:
        profile = StepProfile()

        session, session_get_ms, session_parse_ms = await self._sessions.get_timed(session_id)
        profile.redis_get_ms += session_get_ms
        profile.serialization_ms += session_parse_ms
        if session is None:
            raise SessionNotFoundError(session_id)

        started = time.perf_counter()
        eaten_token = resolve_token(
            session.mode,
            session.model,
            eaten_token_id,
            dynamic_tokens=session.dynamic_tokens,
        )
        if eaten_token is None:
            raise InvalidTokenError(eaten_token_id)
        profile.business_ms += _elapsed_ms(started)

        cached, cache_get_ms, cache_parse_ms = await self._cache.get_timed(
            session_id, eaten_token_id
        )
        profile.redis_get_ms += cache_get_ms
        profile.serialization_ms += cache_parse_ms
        cache_hit = cached is not None

        started = time.perf_counter()
        if cache_hit:
            next_tokens = cached
            if settings.log_step_cache_hit:
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
                current_prompt=session.current_prompt,
                eaten_token_id=eaten_token_id,
                eaten_text=eaten_token.text,
            )
            logger.info(
                "step_cache_miss",
                session_id=session_id,
                trace_id=trace_id,
                eaten_token_id=eaten_token_id,
            )
        profile.business_ms += _elapsed_ms(started)

        started = time.perf_counter()
        is_eos = eaten_token.is_eos
        prior_history = list(session.step_history)
        initial_text = initial_prompt_segment(session.current_prompt, prior_history)
        temperature = derive_temperature(
            eaten_token.prob,
            current=session.current_temperature,
        )
        new_record = StepRecord(
            step_index=current_snake_length,
            token_id=eaten_token_id,
            text=eaten_token.text,
            prob=eaten_token.prob,
            temperature=temperature,
            is_eos=is_eos,
        )
        session.step_history.append(new_record)
        session.current_prompt = rebuild_sliding_prompt(initial_text, session.step_history)
        session.snake_length = current_snake_length
        session.current_temperature = temperature
        session.current_node_id = eaten_token_id
        session.score += round(eaten_token.prob * 100)

        if is_eos:
            session.game_status = "ENDED"
            next_tokens = []
        else:
            session.game_status = "PLAYING"
        register_dynamic_tokens(session, next_tokens or [])
        profile.business_ms += _elapsed_ms(started)

        session_save_ms, session_set_ms = await self._sessions.save_timed(session)
        profile.serialization_ms += session_save_ms
        profile.redis_set_ms += session_set_ms

        if is_eos and self._finalize is not None:
            await self._finalize.finalize_eos(session)

        started = time.perf_counter()
        if not is_eos and next_tokens:
            await self._prefetcher.schedule(
                session_id=session_id,
                trace_id=trace_id,
                mode=session.mode,
                model=session.model,
                current_prompt=session.current_prompt,
                branch_tokens=next_tokens,
            )
        profile.business_ms += _elapsed_ms(started)

        started = time.perf_counter()
        response = StepResponse(
            session_id=session_id,
            game_status=session.game_status,
            current_temperature=temperature,
            snake_speed_multiplier=derive_speed_multiplier(temperature),
            next_tokens_food=next_tokens or [],
            cache_hit=cache_hit,
        )
        profile.serialization_ms += _elapsed_ms(started)

        return response, profile


class SessionNotFoundError(Exception):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Session not found: {session_id}")


class InvalidTokenError(Exception):
    def __init__(self, token_id: str) -> None:
        self.token_id = token_id
        super().__init__(f"Invalid token: {token_id}")
