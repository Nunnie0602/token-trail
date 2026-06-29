import pytest


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "token-trail-api"
    assert payload["redis"] is True


@pytest.mark.asyncio
async def test_create_session(client):
    response = await client.post(
        "/api/v1/session",
        json={"mode": "classic", "model": "qwen"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["session_id"]
    assert payload["game_status"] == "PLAYING"
    assert len(payload["next_tokens_food"]) == 4


@pytest.mark.asyncio
async def test_get_session_404(client):
    response = await client.get("/api/v1/session/does-not-exist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_step_cache_miss_fallback(client):
    create = await client.post("/api/v1/session", json={"mode": "classic", "model": "qwen"})
    session_id = create.json()["session_id"]
    first_token = create.json()["next_tokens_food"][0]["token_id"]

    step = await client.post(
        "/api/v1/game/step",
        json={
            "session_id": session_id,
            "eaten_token_id": first_token,
            "current_snake_length": 2,
        },
    )
    assert step.status_code == 200
    body = step.json()
    assert body["game_status"] == "PLAYING"
    assert len(body["next_tokens_food"]) == 4


@pytest.mark.asyncio
async def test_leaderboard_flow(client):
    create = await client.post("/api/v1/session", json={"mode": "classic", "model": "qwen"})
    session_id = create.json()["session_id"]

    submit = await client.post(
        "/api/v1/leaderboard",
        json={"player_name": "Tester", "score": 300, "session_id": session_id},
    )
    assert submit.status_code == 204

    listing = await client.get("/api/v1/leaderboard")
    assert listing.status_code == 200
    entries = listing.json()["entries"]
    assert any(entry["player_name"] == "Tester" for entry in entries)
