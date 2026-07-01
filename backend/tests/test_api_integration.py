import pytest
from tests.test_e2e_game_flow import _play_until_ended


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

    finalize = await client.post(
        "/api/v1/game/finalize",
        json={
            "session_id": session_id,
            "completion_type": "collision",
            "failure_reason": "collision",
        },
    )
    assert finalize.status_code == 201

    submit = await client.post(
        "/api/v1/leaderboard",
        json={"player_name": "Tester", "score": 300, "session_id": session_id},
    )
    assert submit.status_code == 409

    eos_id, _, _ = await _play_until_ended(client)
    result = await client.get(f"/api/v1/game/result/{eos_id}")
    assert result.status_code == 200

    submit_eos = await client.post(
        "/api/v1/leaderboard",
        json={"player_name": "Tester", "score": 999999, "session_id": eos_id},
    )
    assert submit_eos.status_code == 204

    listing = await client.get("/api/v1/leaderboard")
    assert listing.status_code == 200
    entries = listing.json()["entries"]
    eos_entry = next(entry for entry in entries if entry["session_id"] == eos_id)
    assert eos_entry["player_name"] == "Tester"
    assert eos_entry["score"] != 999999
