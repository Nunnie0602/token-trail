import pytest
from app.models.schemas import StepRecord
from app.services.leaderboard import LeaderboardService
from app.services.result import ResultManager, generate_result
from app.services.session import PlayerSession


@pytest.mark.asyncio
async def test_leaderboard_submit_eos(fake_redis):
    results = ResultManager(fake_redis)
    session = PlayerSession(
        session_id="sess-abc",
        mode="classic",
        model="qwen",
        game_status="ENDED",
        current_prompt="test",
        current_temperature=1.0,
        snake_length=3,
        current_node_id="C_L1A",
        score=215,
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
    await results.save(generate_result(session, "eos"))

    service = LeaderboardService(fake_redis, results)
    await service.submit("PlayerA", 999, "sess-abc")
    entries = await service.top()
    assert len(entries) == 1
    assert entries[0].player_name == "PlayerA"
    assert entries[0].score == 215
    assert entries[0].session_id == "sess-abc"


@pytest.mark.asyncio
async def test_leaderboard_top_100(fake_redis):
    results = ResultManager(fake_redis)
    service = LeaderboardService(fake_redis, results)
    for index in range(150):
        session_id = f"s{index}"
        session = PlayerSession(
            session_id=session_id,
            mode="classic",
            model="qwen",
            game_status="ENDED",
            current_prompt="test",
            current_temperature=1.0,
            snake_length=3,
            current_node_id="C_L1A",
            score=index,
            step_history=[
                StepRecord(
                    step_index=2,
                    token_id="C_L1A",
                    text="聽見敲門",
                    prob=0.5,
                    temperature=1.0,
                    is_eos=False,
                )
            ],
            updated_at="2026-07-01T00:00:00+00:00",
        )
        await results.save(generate_result(session, "eos"))
        await service.submit(f"P{index}", index, session_id)

    entries = await service.top(100)
    assert len(entries) == 100
    assert entries[0].score == 149
    assert entries[-1].score == 50
