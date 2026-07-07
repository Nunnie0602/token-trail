import asyncio

from app.ai.inference import InferenceService
from app.cache.branch_cache import BranchCache
from app.core.logging import logger
from app.models.schemas import GameMode, ModelProfile, TokenFood


class PrefetchScheduler:
    def __init__(
        self,
        cache: BranchCache,
        inference: InferenceService | None = None,
        *,
        enabled: bool = True,
    ) -> None:
        self._cache = cache
        self._inference = inference or InferenceService()
        self._enabled = enabled

    async def schedule(
        self,
        *,
        session_id: str,
        trace_id: str,
        mode: GameMode,
        model: ModelProfile,
        current_prompt: str,
        branch_tokens: list[TokenFood],
    ) -> None:
        if not self._enabled:
            return
        asyncio.create_task(
            self._prefetch_branches(
                session_id=session_id,
                trace_id=trace_id,
                mode=mode,
                model=model,
                current_prompt=current_prompt,
                branch_tokens=branch_tokens,
            )
        )

    async def _prefetch_branches(
        self,
        *,
        session_id: str,
        trace_id: str,
        mode: GameMode,
        model: ModelProfile,
        current_prompt: str,
        branch_tokens: list[TokenFood],
    ) -> None:
        try:
            tasks = [
                self._prefetch_one(
                    session_id=session_id,
                    mode=mode,
                    model=model,
                    current_prompt=current_prompt,
                    branch=branch,
                )
                for branch in branch_tokens[:4]
                if not branch.is_eos
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            branches: dict[str, list[TokenFood]] = {}
            for result in results:
                if isinstance(result, BaseException):
                    logger.warning(
                        "prefetch_branch_failed",
                        session_id=session_id,
                        trace_id=trace_id,
                        error=str(result),
                    )
                    continue
                token_id, tokens = result
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

    async def _prefetch_one(
        self,
        *,
        session_id: str,
        mode: GameMode,
        model: ModelProfile,
        current_prompt: str,
        branch: TokenFood,
    ) -> tuple[str, list[TokenFood]]:
        story_context = f"{current_prompt}{branch.text}"
        tokens = await self._inference.predict_next_tokens(
            prompt=story_context,
            mode=mode,
            model=model,
            corpus_token_id=branch.token_id,
        )
        return branch.token_id, tokens

    async def seed_branches(
        self,
        *,
        session_id: str,
        mode: GameMode,
        model: ModelProfile,
        current_prompt: str,
        branch_tokens: list[TokenFood],
    ) -> None:
        await self._prefetch_branches(
            session_id=session_id,
            trace_id="seed",
            mode=mode,
            model=model,
            current_prompt=current_prompt,
            branch_tokens=branch_tokens,
        )
