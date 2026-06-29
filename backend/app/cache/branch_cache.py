import json
from typing import Any

from redis.asyncio import Redis

from app.cache.keys import CACHE_TTL_SECONDS, prefetch_key
from app.models.schemas import TokenFood


class BranchCache:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get(self, session_id: str, eaten_token_id: str) -> list[TokenFood] | None:
        raw = await self._redis.get(prefetch_key(session_id, eaten_token_id))
        if raw is None:
            return None
        payload = json.loads(raw)
        return [TokenFood.model_validate(item) for item in payload["next_tokens_food"]]

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
