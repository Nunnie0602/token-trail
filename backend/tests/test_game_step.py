import asyncio

import pytest
from app.cache.branch_cache import BranchCache
from app.services.fallback import FallbackService
from app.services.game_step import GameStepService, SessionNotFoundError
from app.services.prefetcher import PrefetchScheduler
from app.services.session import SessionManager


@pytest.mark.asyncio
async def test_step_updates_prompt(fake_redis):
    sessions = SessionManager(fake_redis)
    session = await sessions.create("classic", "qwen")
    original_prompt = session.current_prompt

    service = GameStepService(
        sessions=sessions,
        cache=BranchCache(fake_redis),
        fallback=FallbackService(),
        prefetcher=PrefetchScheduler(BranchCache(fake_redis)),
    )
    response = await service.execute(
        session_id=session.session_id,
        eaten_token_id="C_L1A",
        current_snake_length=2,
        trace_id="trace-1",
    )

    updated = await sessions.get(session.session_id)
    assert updated is not None
    assert updated.current_prompt.startswith(original_prompt)
    assert "聽見敲門" in updated.current_prompt
    assert len(response.next_tokens_food) == 4


@pytest.mark.asyncio
async def test_step_cache_hit(fake_redis):
    sessions = SessionManager(fake_redis)
    session = await sessions.create("classic", "qwen")
    cache = BranchCache(fake_redis)

    from app.models.schemas import TokenFood

    cached_tokens = [
        TokenFood(token_id="X1", text="打開門縫", prob=0.71),
        TokenFood(token_id="X2", text="裝作沒聽見", prob=0.15),
        TokenFood(token_id="X3", text="拿起掃把防身", prob=0.09),
        TokenFood(token_id="X4", text="開始直播求援", prob=0.05),
    ]
    await cache.set(session.session_id, "C_L1A", cached_tokens)

    service = GameStepService(
        sessions=sessions,
        cache=cache,
        fallback=FallbackService(),
        prefetcher=PrefetchScheduler(cache),
    )
    response = await service.execute(
        session_id=session.session_id,
        eaten_token_id="C_L1A",
        current_snake_length=2,
        trace_id="trace-hit",
    )
    assert response.cache_hit is True
    assert response.next_tokens_food[0].text == "打開門縫"


@pytest.mark.asyncio
async def test_step_session_not_found(fake_redis):
    service = GameStepService(
        sessions=SessionManager(fake_redis),
        cache=BranchCache(fake_redis),
        fallback=FallbackService(),
        prefetcher=PrefetchScheduler(BranchCache(fake_redis)),
    )
    with pytest.raises(SessionNotFoundError):
        await service.execute(
            session_id="missing",
            eaten_token_id="C_L1A",
            current_snake_length=2,
            trace_id="trace-miss",
        )


@pytest.mark.asyncio
async def test_prefetch_writes_branches(fake_redis):
    sessions = SessionManager(fake_redis)
    session = await sessions.create("classic", "qwen")
    cache = BranchCache(fake_redis)
    prefetcher = PrefetchScheduler(cache)

    await prefetcher.seed_branches(
        session_id=session.session_id,
        mode="classic",
        model="qwen",
        branch_token_ids=["C_L1A", "C_L1B", "C_L1C", "C_L1D"],
    )
    await asyncio.sleep(0.05)

    assert await cache.get(session.session_id, "C_L1A") is not None
    assert await cache.get(session.session_id, "C_L1B") is not None
