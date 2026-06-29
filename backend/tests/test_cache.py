import pytest
from app.cache.branch_cache import BranchCache
from app.models.schemas import TokenFood
from app.services.fallback import FallbackService
from app.services.temperature import derive_temperature


@pytest.mark.asyncio
async def test_branch_cache_roundtrip(fake_redis):
    cache = BranchCache(fake_redis)
    tokens = [
        TokenFood(token_id="A", text="聽見敲門", prob=0.78),
        TokenFood(token_id="B", text="發現奏摺", prob=0.11),
        TokenFood(token_id="C", text="撿到珍珠奶茶", prob=0.05),
        TokenFood(token_id="D", text="看見窗外有鬼影", prob=0.02),
    ]
    await cache.set("sess1", "CLASSIC_ACT_01", tokens)
    loaded = await cache.get("sess1", "CLASSIC_ACT_01")
    assert loaded is not None
    assert len(loaded) == 4
    assert loaded[0].text == "聽見敲門"


@pytest.mark.asyncio
async def test_fallback_on_cache_miss():
    service = FallbackService()
    tokens = await service.resolve(
        session_id="s1",
        trace_id="t1",
        mode="classic",
        model="qwen",
        eaten_token_id="C_L1A",
    )
    assert len(tokens) == 4


def test_temperature_increases_on_low_prob():
    high_prob_temp = derive_temperature(0.9)
    low_prob_temp = derive_temperature(0.1)
    assert low_prob_temp > high_prob_temp
