import json
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from redis.asyncio import Redis

from app.cache.keys import SESSION_TTL_SECONDS, session_key
from app.models.schemas import GameMode, GameStatus, ModelProfile, TokenFood
from app.services.corpus import get_next_tokens, pick_initial_token


@dataclass
class PlayerSession:
    session_id: str
    mode: GameMode
    model: ModelProfile
    game_status: GameStatus
    current_prompt: str
    current_temperature: float
    snake_length: int
    current_node_id: str | None
    score: int
    updated_at: str

    def to_dict(self) -> dict[str, str | int | float | None]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "PlayerSession":
        return cls(
            session_id=str(data["session_id"]),
            mode=str(data["mode"]),  # type: ignore[arg-type]
            model=str(data["model"]),  # type: ignore[arg-type]
            game_status=str(data["game_status"]),  # type: ignore[arg-type]
            current_prompt=str(data["current_prompt"]),
            current_temperature=float(str(data["current_temperature"])),
            snake_length=int(str(data["snake_length"])),
            current_node_id=str(data["current_node_id"]) if data.get("current_node_id") else None,
            score=int(str(data.get("score", 0))),
            updated_at=str(data["updated_at"]),
        )


class SessionManager:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def create(self, mode: GameMode, model: ModelProfile) -> PlayerSession:
        initial = pick_initial_token(mode)
        now = datetime.now(UTC).isoformat()
        session = PlayerSession(
            session_id=str(uuid.uuid4())[:13],
            mode=mode,
            model=model,
            game_status="PLAYING",
            current_prompt=initial["text"],
            current_temperature=1.0,
            snake_length=1,
            current_node_id=initial["token_id"],
            score=0,
            updated_at=now,
        )
        await self.save(session)
        return session

    async def get(self, session_id: str) -> PlayerSession | None:
        raw = await self._redis.get(session_key(session_id))
        if raw is None:
            return None
        return PlayerSession.from_dict(json.loads(raw))

    async def save(self, session: PlayerSession) -> None:
        session.updated_at = datetime.now(UTC).isoformat()
        await self._redis.set(
            session_key(session.session_id),
            json.dumps(session.to_dict(), ensure_ascii=False),
            ex=SESSION_TTL_SECONDS,
        )

    async def ttl(self, session_id: str) -> int:
        ttl = await self._redis.ttl(session_key(session_id))
        return int(ttl)

    def initial_next_tokens(self, session: PlayerSession) -> list[TokenFood]:
        if session.current_node_id is None:
            return []
        return get_next_tokens(session.mode, session.model, session.current_node_id) or []
