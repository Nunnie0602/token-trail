import pytest
from app.services.leaderboard import LeaderboardService


@pytest.mark.asyncio
async def test_leaderboard_submit(fake_redis):
    service = LeaderboardService(fake_redis)
    await service.submit("PlayerA", 215, "sess-abc")
    entries = await service.top()
    assert len(entries) == 1
    assert entries[0].player_name == "PlayerA"
    assert entries[0].score == 215
    assert entries[0].session_id == "sess-abc"


@pytest.mark.asyncio
async def test_leaderboard_top_100(fake_redis):
    service = LeaderboardService(fake_redis)
    for index in range(150):
        await service.submit(f"P{index}", index, f"s{index}")
    entries = await service.top(100)
    assert len(entries) == 100
    assert entries[0].score == 149
    assert entries[-1].score == 50
