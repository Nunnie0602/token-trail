import pytest
from app.services.leaderboard import LeaderboardService
from app.services.result import (
    FinalizeService,
    ResultManager,
    generate_result,
)
from app.services.session import PlayerSession, SessionManager
from app.models.schemas import StepRecord


def _sample_session(**overrides) -> PlayerSession:
    base = PlayerSession(
        session_id="sess-test",
        mode="classic",
        model="qwen",
        game_status="PLAYING",
        current_prompt="夜半時分",
        current_temperature=1.0,
        snake_length=3,
        current_node_id="C_L1A",
        score=78,
        step_history=[
            StepRecord(
                step_index=2,
                token_id="C_L1A",
                text="聽見敲門",
                prob=0.78,
                temperature=1.15,
                is_eos=False,
            )
        ],
        updated_at="2026-07-01T00:00:00+00:00",
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


@pytest.mark.asyncio
async def test_generate_result_is_self_contained():
    session = _sample_session(game_status="COLLISION_FAILED")
    result = generate_result(session, "collision", "collision")

    assert result.session_id == "sess-test"
    assert result.terminal_game_status == "COLLISION_FAILED"
    assert result.completion_type == "collision"
    assert result.failure_reason == "collision"
    assert result.score == 78
    assert result.story_path == ["聽見敲門"]
    assert result.chosen_probs == [0.78]
    assert result.personality_type == "Greedy Searcher"
    assert len(result.step_history) == 1


@pytest.mark.asyncio
async def test_finalize_collision(fake_redis):
    sessions = SessionManager(fake_redis)
    results = ResultManager(fake_redis)
    finalize = FinalizeService(sessions, results)
    session = await sessions.create("classic", "qwen")
    session.step_history.append(
        StepRecord(
            step_index=2,
            token_id="C_L1A",
            text="聽見敲門",
            prob=0.78,
            temperature=1.15,
            is_eos=False,
        )
    )
    session.snake_length = 2
    session.score = 78
    await sessions.save(session)

    result = await finalize.finalize(
        session_id=session.session_id,
        completion_type="collision",
        failure_reason="collision",
    )
    assert result is not None
    assert result.completion_type == "collision"
    assert result.terminal_game_status == "COLLISION_FAILED"

    stored = await results.get(session.session_id)
    assert stored is not None
    assert stored.score == 78


@pytest.mark.asyncio
async def test_abort_below_threshold_no_result(fake_redis):
    sessions = SessionManager(fake_redis)
    results = ResultManager(fake_redis)
    finalize = FinalizeService(sessions, results)
    session = await sessions.create("classic", "qwen")
    session.snake_length = 2
    await sessions.save(session)

    result = await finalize.finalize(
        session_id=session.session_id,
        completion_type="voluntary_exit",
        failure_reason="voluntary_exit",
    )
    assert result is None
    assert await sessions.get(session.session_id) is None
    assert await results.get(session.session_id) is None


@pytest.mark.asyncio
async def test_result_survives_session_expiry(fake_redis):
    sessions = SessionManager(fake_redis)
    results = ResultManager(fake_redis)
    finalize = FinalizeService(sessions, results)
    session = await sessions.create("classic", "qwen")
    session.step_history.append(
        StepRecord(
            step_index=2,
            token_id="C_L1A",
            text="聽見敲門",
            prob=0.78,
            temperature=1.15,
            is_eos=False,
        )
    )
    session.snake_length = 3
    session.score = 78
    await sessions.save(session)

    result = await finalize.finalize(
        session_id=session.session_id,
        completion_type="collision",
        failure_reason="collision",
    )
    assert result is not None

    await sessions.delete(session.session_id)
    assert await sessions.get(session.session_id) is None
    assert await results.get(session.session_id) is not None


@pytest.mark.asyncio
async def test_finalize_api_error(fake_redis):
    sessions = SessionManager(fake_redis)
    results = ResultManager(fake_redis)
    finalize = FinalizeService(sessions, results)
    session = await sessions.create("classic", "qwen")
    session.step_history.append(
        StepRecord(
            step_index=2,
            token_id="C_L1A",
            text="聽見敲門",
            prob=0.78,
            temperature=1.15,
            is_eos=False,
        )
    )
    session.snake_length = 2
    session.score = 78
    await sessions.save(session)

    result = await finalize.finalize(
        session_id=session.session_id,
        completion_type="api_error",
        failure_reason="api_error",
    )
    assert result is not None
    assert result.completion_type == "api_error"
    assert result.terminal_game_status == "ABORTED"
    assert result.failure_reason == "api_error"


@pytest.mark.asyncio
async def test_finalize_tab_closed_preserves_failure_reason(fake_redis):
    sessions = SessionManager(fake_redis)
    results = ResultManager(fake_redis)
    finalize = FinalizeService(sessions, results)
    session = await sessions.create("classic", "qwen")
    session.step_history.append(
        StepRecord(
            step_index=2,
            token_id="C_L1A",
            text="聽見敲門",
            prob=0.78,
            temperature=1.15,
            is_eos=False,
        )
    )
    session.snake_length = 3
    session.score = 78
    await sessions.save(session)

    result = await finalize.finalize(
        session_id=session.session_id,
        completion_type="voluntary_exit",
        failure_reason="tab_closed",
    )
    assert result is not None
    assert result.completion_type == "voluntary_exit"
    assert result.failure_reason == "tab_closed"


@pytest.mark.asyncio
async def test_finalize_rejects_client_story_path(client):
    create = await client.post("/api/v1/session", json={"mode": "classic", "model": "qwen"})
    session_id = create.json()["session_id"]

    response = await client.post(
        "/api/v1/game/finalize",
        json={
            "session_id": session_id,
            "completion_type": "collision",
            "failure_reason": "collision",
            "story_path": ["tampered"],
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_leaderboard_ignores_client_score_inflation(fake_redis):
    sessions = SessionManager(fake_redis)
    results = ResultManager(fake_redis)
    session = _sample_session(game_status="ENDED")
    result = generate_result(session, "eos")
    await results.save(result)

    service = LeaderboardService(fake_redis, results)
    await service.submit("PlayerA", 999999, "sess-test")

    entries = await service.top()
    assert entries[0].score == 78


@pytest.mark.asyncio
async def test_leaderboard_rejects_non_eos(fake_redis):
    sessions = SessionManager(fake_redis)
    results = ResultManager(fake_redis)
    session = _sample_session(game_status="COLLISION_FAILED")
    result = generate_result(session, "collision", "collision")
    await results.save(result)

    service = LeaderboardService(fake_redis, results)
    from app.services.result import LeaderboardNotEligibleError

    with pytest.raises(LeaderboardNotEligibleError):
        await service.submit("PlayerA", 78, "sess-test")
