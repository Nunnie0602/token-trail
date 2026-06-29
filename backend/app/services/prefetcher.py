import asyncio

from app.cache.branch_cache import BranchCache
from app.core.logging import logger
from app.models.schemas import GameMode, ModelProfile, TokenFood
from app.services.mock_llm import MockLLM


class PrefetchScheduler:
    def __init__(
        self,
        cache: BranchCache,
        mock_llm: MockLLM | None = None,
        *,
        enabled: bool = True,
    ) -> None:
        self._cache = cache
        self._mock_llm = mock_llm or MockLLM()
        self._enabled = enabled

    async def schedule(
        self,
        *,
        session_id: str,
        trace_id: str,
        mode: GameMode,
        model: ModelProfile,
        branch_token_ids: list[str],
    ) -> None:
        if not self._enabled:
            return
        asyncio.create_task(
            self._prefetch_branches(
                session_id=session_id,
                trace_id=trace_id,
                mode=mode,
                model=model,
                branch_token_ids=branch_token_ids,
            )
        )

    async def _prefetch_branches(
        self,
        *,
        session_id: str,
        trace_id: str,
        mode: GameMode,
        model: ModelProfile,
        branch_token_ids: list[str],
    ) -> None:
        try:
            branches: dict[str, list[TokenFood]] = {}
            for token_id in branch_token_ids[:4]:
                tokens = await self._mock_llm.predict_next_tokens(mode, model, token_id)
                if tokens:
                    branches[token_id] = tokens

            if branches:
                await self._cache.set_batch(session_id, branches)
                logger.info(
                    "prefetch_completed",
                    session_id=session_id,
                    trace_id=trace_id,
                    branch_count=len(branches),
                )
        except Exception as exc:
            logger.error(
                "prefetch_failed",
                session_id=session_id,
                trace_id=trace_id,
                error=str(exc),
            )

    async def seed_branches(
        self,
        *,
        session_id: str,
        mode: GameMode,
        model: ModelProfile,
        branch_token_ids: list[str],
    ) -> None:
        await self._prefetch_branches(
            session_id=session_id,
            trace_id="seed",
            mode=mode,
            model=model,
            branch_token_ids=branch_token_ids,
        )
