import pytest_asyncio
from app.api.deps import build_game_step_service
from app.main import app
from fakeredis import aioredis as fakeredis
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def fake_redis():
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def client(fake_redis):
    app.state.redis = fake_redis
    app.state.game_step_service = build_game_step_service(fake_redis)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
