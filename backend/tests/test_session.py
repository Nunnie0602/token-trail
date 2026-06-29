import pytest
from app.cache.keys import CACHE_TTL_SECONDS, prefetch_key, session_key
from app.services.session import SessionManager


@pytest.mark.asyncio
async def test_session_create_and_read(fake_redis):
    manager = SessionManager(fake_redis)
    session = await manager.create("classic", "qwen")

    assert len(session.session_id) == 13
    assert session.mode == "classic"
    assert session.model == "qwen"
    assert session.game_status == "PLAYING"
    assert session.current_temperature == 1.0
    assert session.snake_length == 1
    assert session.current_prompt

    loaded = await manager.get(session.session_id)
    assert loaded is not None
    assert loaded.session_id == session.session_id


@pytest.mark.asyncio
async def test_session_ttl(fake_redis):
    manager = SessionManager(fake_redis)
    session = await manager.create("classic", "qwen")
    ttl = await fake_redis.ttl(session_key(session.session_id))
    assert 1790 <= ttl <= CACHE_TTL_SECONDS


def test_prefetch_key_format():
    key = prefetch_key("abc-123", "CLASSIC_ACT_01")
    assert key == "prefetch:abc-123:CLASSIC_ACT_01"
