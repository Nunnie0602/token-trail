import json
from datetime import UTC, datetime

from redis.asyncio import Redis

from app.cache.keys import RESULT_TTL_SECONDS, result_key
from app.models.schemas import (
    GameCompletionType,
    GameResult,
    GameStatus,
    TerminalGameStatus,
)
from app.services.personality import decode_personality
from app.services.session import PlayerSession, SessionManager

_COMPLETION_TO_STATUS: dict[GameCompletionType, TerminalGameStatus] = {
    "eos": "ENDED",
    "collision": "COLLISION_FAILED",
    "voluntary_exit": "ABORTED",
    "api_error": "ABORTED",
}


def resolve_terminal_status(
    completion_type: GameCompletionType,
) -> TerminalGameStatus:
    return _COMPLETION_TO_STATUS[completion_type]


def generate_result(
    session: PlayerSession,
    completion_type: GameCompletionType,
    failure_reason: str | None = None,
) -> GameResult:
    chosen_probs = [record.prob for record in session.step_history]
    personality_type, personality_description = decode_personality(chosen_probs)
    terminal_status = resolve_terminal_status(completion_type)

    return GameResult(
        session_id=session.session_id,
        terminal_game_status=terminal_status,
        completion_type=completion_type,
        failure_reason=failure_reason,
        mode=session.mode,
        model=session.model,
        score=session.score,
        snake_length=session.snake_length,
        story_path=[record.text for record in session.step_history],
        chosen_probs=chosen_probs,
        temperature_history=[record.temperature for record in session.step_history],
        step_history=session.step_history,
        personality_type=personality_type,
        personality_description=personality_description,
        created_at=datetime.now(UTC).isoformat(),
    )


class ResultManager:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get(self, session_id: str) -> GameResult | None:
        raw = await self._redis.get(result_key(session_id))
        if raw is None:
            return None
        return GameResult.model_validate(json.loads(raw))

    async def save(self, result: GameResult) -> None:
        payload = json.dumps(result.model_dump(), ensure_ascii=False)
        await self._redis.set(
            result_key(result.session_id),
            payload,
            ex=RESULT_TTL_SECONDS,
        )

    async def delete(self, session_id: str) -> None:
        await self._redis.delete(result_key(session_id))


class FinalizeService:
    def __init__(self, sessions: SessionManager, results: ResultManager) -> None:
        self._sessions = sessions
        self._results = results

    async def persist_result(
        self,
        session: PlayerSession,
        completion_type: GameCompletionType,
        failure_reason: str | None = None,
    ) -> GameResult:
        existing = await self._results.get(session.session_id)
        if existing is not None:
            return existing

        result = generate_result(session, completion_type, failure_reason)
        await self._results.save(result)
        return result

    async def finalize_eos(self, session: PlayerSession) -> GameResult:
        return await self.persist_result(session, "eos")

    async def finalize(
        self,
        *,
        session_id: str,
        completion_type: GameCompletionType,
        failure_reason: str | None = None,
    ) -> GameResult | None:
        session = await self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)

        if completion_type == "voluntary_exit" and session.snake_length < 3:
            await self._sessions.delete(session_id)
            return None

        existing = await self._results.get(session_id)
        if existing is not None:
            return existing

        if session.game_status == "ENDED" and completion_type == "eos":
            return await self.persist_result(session, "eos", failure_reason)

        if session.game_status != "PLAYING":
            raise InvalidFinalizeStateError(session_id, session.game_status)

        terminal_status: GameStatus = resolve_terminal_status(completion_type)
        session.game_status = terminal_status
        await self._sessions.save(session)
        return await self.persist_result(session, completion_type, failure_reason)


class SessionNotFoundError(Exception):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Session not found: {session_id}")


class InvalidFinalizeStateError(Exception):
    def __init__(self, session_id: str, game_status: str) -> None:
        self.session_id = session_id
        self.game_status = game_status
        super().__init__(
            f"Cannot finalize session {session_id} in state {game_status}",
        )


class ResultNotFoundError(Exception):
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        super().__init__(f"Result not found: {session_id}")


class LeaderboardNotEligibleError(Exception):
    def __init__(self, session_id: str, completion_type: str) -> None:
        self.session_id = session_id
        self.completion_type = completion_type
        super().__init__(
            f"Session {session_id} with completion_type={completion_type} "
            "is not eligible for leaderboard",
        )
