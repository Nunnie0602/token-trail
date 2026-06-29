import json
import time
from typing import Any

from redis.asyncio import Redis

from app.cache.keys import CACHE_TTL_SECONDS, prefetch_key
from app.models.schemas import TokenFood


class BranchCache:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get(self, session_id: str, eaten_token_id: str) -> list[TokenFood] | None:
        tokens, _, _ = await self.get_timed(session_id, eaten_token_id)
        return tokens

    async def get_timed(
        self,
        session_id: str,
        eaten_token_id: str,
    ) -> tuple[list[TokenFood] | None, float, float]:
        redis_started = time.perf_counter()
        raw = await self._redis.get(prefetch_key(session_id, eaten_token_id))
        redis_get_ms = (time.perf_counter() - redis_started) * 1000
        if raw is None:
            return None, redis_get_ms, 0.0
        serialization_started = time.perf_counter()
        payload = json.loads(raw)
        tokens = [TokenFood.model_validate(item) for item in payload["next_tokens_food"]]
        serialization_ms = (time.perf_counter() - serialization_started) * 1000
        return tokens, redis_get_ms, serialization_ms

    async def set(
        self,
        session_id: str,
        eaten_token_id: str,
        tokens: list[TokenFood],
    ) -> None:
        payload = {"next_tokens_food": [token.model_dump() for token in tokens]}
        await self._redis.set(
            prefetch_key(session_id, eaten_token_id),
            json.dumps(payload, ensure_ascii=False),
            ex=CACHE_TTL_SECONDS,
        )

    async def set_batch(
        self,
        session_id: str,
        branches: dict[str, list[TokenFood]],
    ) -> None:
        if not branches:
            return
        pipe = self._redis.pipeline()
        for token_id, tokens in branches.items():
            payload: dict[str, Any] = {
                "next_tokens_food": [token.model_dump() for token in tokens],
            }
            pipe.set(
                prefetch_key(session_id, token_id),
                json.dumps(payload, ensure_ascii=False),
                ex=CACHE_TTL_SECONDS,
            )
        await pipe.execute()
