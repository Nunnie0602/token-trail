import asyncio
import time

from app.ai.inference import InferenceService
from app.cache.branch_cache import BranchCache
from app.core.config import settings
from app.core.logging import logger
from app.models.schemas import GameMode, ModelProfile, TokenFood
from app.services.token_source import classify_token_source


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
            active_branches = [
                branch for branch in branch_tokens[:4] if not branch.is_eos
            ]
            concurrency = min(settings.prefetch_concurrency, len(active_branches))
            if concurrency == 0:
                return

            semaphore = asyncio.Semaphore(concurrency)
            branch_metrics: list[dict[str, object]] = []

            async def _run_prefetch(branch: TokenFood) -> tuple[str, list[TokenFood]]:
                queued_at = time.perf_counter()
                async with semaphore:
                    started_at = time.perf_counter()
                    queue_wait_ms = round((started_at - queued_at) * 1000, 2)
                    token_id, tokens = await self._prefetch_one(
                        session_id=session_id,
                        mode=mode,
                        model=model,
                        current_prompt=current_prompt,
                        branch=branch,
                    )
                    branch_total_ms = round((time.perf_counter() - queued_at) * 1000, 2)
                    token_source = classify_token_source(tokens)
                    metric = {
                        "branch_token_id": branch.token_id,
                        "queue_wait_ms": queue_wait_ms,
                        "branch_total_ms": branch_total_ms,
                        "token_source": token_source,
                        "token_count": len(tokens),
                    }
                    branch_metrics.append(metric)
                    logger.info(
                        "prefetch_branch_metrics",
                        session_id=session_id,
                        trace_id=trace_id,
                        **metric,
                    )
                    return token_id, tokens

            results = await asyncio.gather(
                *[_run_prefetch(branch) for branch in active_branches],
                return_exceptions=True,
            )

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
                queue_waits = [
                    float(value)
                    for metric in branch_metrics
                    if isinstance(value := metric.get("queue_wait_ms"), int | float)
                ]
                branch_totals = [
                    float(value)
                    for metric in branch_metrics
                    if isinstance(value := metric.get("branch_total_ms"), int | float)
                ]
                source_counts = {
                    source: sum(
                        1
                        for metric in branch_metrics
                        if metric.get("token_source") == source
                    )
                    for source in ("inference", "corpus", "static", "empty", "unknown")
                }
                logger.info(
                    "prefetch_completed",
                    session_id=session_id,
                    trace_id=trace_id,
                    branch_count=len(branches),
                    prefetch_concurrency=concurrency,
                    branch_metrics=branch_metrics,
                    inference_branch_count=source_counts["inference"],
                    corpus_branch_count=source_counts["corpus"],
                    static_branch_count=source_counts["static"],
                    avg_queue_wait_ms=round(sum(queue_waits) / len(queue_waits), 2)
                    if queue_waits
                    else 0.0,
                    max_queue_wait_ms=round(max(queue_waits), 2) if queue_waits else 0.0,
                    avg_branch_total_ms=round(sum(branch_totals) / len(branch_totals), 2)
                    if branch_totals
                    else 0.0,
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
