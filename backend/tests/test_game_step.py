import asyncio

import pytest
from app.cache.branch_cache import BranchCache
from app.services.fallback import FallbackService
from app.services.game_step import GameStepService, InvalidTokenError, SessionNotFoundError
from app.services.prefetcher import PrefetchScheduler
from app.services.result import FinalizeService, ResultManager
from app.services.session import SessionManager


def _build_step_service(fake_redis, *, cache=None, prefetcher=None) -> GameStepService:
    sessions = SessionManager(fake_redis)
    results = ResultManager(fake_redis)
    finalize = FinalizeService(sessions, results)
    branch_cache = cache or BranchCache(fake_redis)
    scheduler = prefetcher or PrefetchScheduler(branch_cache)
    return GameStepService(
        sessions=sessions,
        cache=branch_cache,
        fallback=FallbackService(),
        prefetcher=scheduler,
        finalize=finalize,
    )


@pytest.mark.asyncio
async def test_step_accumulates_history_and_score(fake_redis):
    sessions = SessionManager(fake_redis)
    session = await sessions.create("classic", "qwen")
    service = _build_step_service(fake_redis)

    await service.execute(
        session_id=session.session_id,
        eaten_token_id="C_L1A",
        current_snake_length=2,
        trace_id="trace-history",
    )

    updated = await sessions.get(session.session_id)
    assert updated is not None
    assert len(updated.step_history) == 1
    record = updated.step_history[0]
    assert record.step_index == 2
    assert record.token_id == "C_L1A"
    assert record.text == "聽見敲門"
    assert updated.score == round(record.prob * 100)


@pytest.mark.asyncio
async def test_step_updates_prompt(fake_redis):
    sessions = SessionManager(fake_redis)
    session = await sessions.create("classic", "qwen")
    original_prompt = session.current_prompt

    service = _build_step_service(fake_redis)
    response, _ = await service.execute(
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

    service = _build_step_service(fake_redis, cache=cache, prefetcher=PrefetchScheduler(cache))
    response, _ = await service.execute(
        session_id=session.session_id,
        eaten_token_id="C_L1A",
        current_snake_length=2,
        trace_id="trace-hit",
    )
    assert response.cache_hit is True
    assert response.next_tokens_food[0].text == "打開門縫"


@pytest.mark.asyncio
async def test_step_session_not_found(fake_redis):
    service = _build_step_service(fake_redis)
    with pytest.raises(SessionNotFoundError):
        await service.execute(
            session_id="missing",
            eaten_token_id="C_L1A",
            current_snake_length=2,
            trace_id="trace-miss",
        )


@pytest.mark.asyncio
async def test_prefetch_disabled_skips_background_schedule(fake_redis):
    sessions = SessionManager(fake_redis)
    session = await sessions.create("classic", "qwen")
    cache = BranchCache(fake_redis)
    prefetcher = PrefetchScheduler(cache, enabled=False)

    from app.models.schemas import TokenFood

    cached_tokens = [
        TokenFood(token_id="X1", text="打開門縫", prob=0.71),
        TokenFood(token_id="X2", text="裝作沒聽見", prob=0.15),
        TokenFood(token_id="X3", text="拿起掃把防身", prob=0.09),
        TokenFood(token_id="X4", text="開始直播求援", prob=0.05),
    ]
    await cache.set(session.session_id, "C_L1A", cached_tokens)

    service = _build_step_service(fake_redis, cache=cache, prefetcher=prefetcher)
    await service.execute(
        session_id=session.session_id,
        eaten_token_id="C_L1A",
        current_snake_length=2,
        trace_id="trace-no-prefetch",
    )
    await asyncio.sleep(0.05)

    assert await cache.get(session.session_id, "X1") is None


@pytest.mark.asyncio
async def test_step_profile_segments_on_cache_hit(fake_redis):
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

    service = _build_step_service(
        fake_redis,
        cache=cache,
        prefetcher=PrefetchScheduler(cache, enabled=False),
    )
    _, profile = await service.execute(
        session_id=session.session_id,
        eaten_token_id="C_L1A",
        current_snake_length=2,
        trace_id="trace-profile",
    )

    assert profile.redis_get_ms >= 0
    assert profile.redis_set_ms >= 0
    assert profile.business_ms >= 0
    assert profile.serialization_ms >= 0
    assert profile.accounted_ms > 0


@pytest.mark.asyncio
async def test_prefetch_writes_branches(fake_redis):

    sessions = SessionManager(fake_redis)
    session = await sessions.create("classic", "qwen")
    cache = BranchCache(fake_redis)
    prefetcher = PrefetchScheduler(cache)
    next_tokens = sessions.initial_next_tokens(session)

    await prefetcher.seed_branches(
        session_id=session.session_id,
        mode="classic",
        model="qwen",
        current_prompt=session.current_prompt,
        branch_tokens=next_tokens,
    )
    await asyncio.sleep(0.05)

    for token in next_tokens:
        assert await cache.get(session.session_id, token.token_id) is not None


@pytest.mark.asyncio
async def test_step_continues_after_eating_dynamic_inf_token(fake_redis):
    from app.models.schemas import TokenFood

    sessions = SessionManager(fake_redis)
    session = await sessions.create("classic", "qwen")
    cache = BranchCache(fake_redis)

    first_branch_tokens = [
        TokenFood(token_id="INF_AAAA1111", text="打開門縫", prob=0.4),
        TokenFood(token_id="INF_BBBB2222", text="裝作沒聽見", prob=0.28),
        TokenFood(token_id="INF_CCCC3333", text="拿起掃把", prob=0.2),
        TokenFood(token_id="INF_DDDD4444", text="開始直播", prob=0.12),
    ]
    second_branch_tokens = [
        TokenFood(token_id="INF_EEEE5555", text="聽見腳步", prob=0.4),
        TokenFood(token_id="INF_FFFF6666", text="心裡一緊", prob=0.28),
        TokenFood(token_id="INF_GGGG7777", text="窗外輕風", prob=0.2),
        TokenFood(token_id="INF_HHHH8888", text="夜色更深", prob=0.12),
    ]
    await cache.set(session.session_id, "C_L1A", first_branch_tokens)
    await cache.set(session.session_id, "INF_AAAA1111", second_branch_tokens)

    service = _build_step_service(
        fake_redis,
        cache=cache,
        prefetcher=PrefetchScheduler(cache, enabled=False),
    )
    first_response, _ = await service.execute(
        session_id=session.session_id,
        eaten_token_id="C_L1A",
        current_snake_length=2,
        trace_id="trace-inf-1",
    )
    assert first_response.next_tokens_food[0].token_id.startswith("INF_")

    second_response, _ = await service.execute(
        session_id=session.session_id,
        eaten_token_id="INF_AAAA1111",
        current_snake_length=3,
        trace_id="trace-inf-2",
    )
    assert second_response.game_status == "PLAYING"
    assert second_response.next_tokens_food[0].token_id == "INF_EEEE5555"

    updated = await sessions.get(session.session_id)
    assert updated is not None
    assert len(updated.step_history) == 2
    assert updated.step_history[1].token_id == "INF_AAAA1111"
    assert "打開門縫" in updated.current_prompt


@pytest.mark.asyncio
async def test_step_rejects_unknown_dynamic_token(fake_redis):
    sessions = SessionManager(fake_redis)
    session = await sessions.create("classic", "qwen")
    service = _build_step_service(fake_redis)

    with pytest.raises(InvalidTokenError):
        await service.execute(
            session_id=session.session_id,
            eaten_token_id="INF_UNKNOWN1",
            current_snake_length=2,
            trace_id="trace-unknown-inf",
        )
