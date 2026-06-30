import pytest


def _pick_token(tokens: list[dict], *, prefer_eos: bool) -> dict:
    if prefer_eos:
        for token in tokens:
            if token.get("is_eos"):
                return token
    non_eos = [token for token in tokens if not token.get("is_eos")]
    pool = non_eos if non_eos else tokens
    return max(pool, key=lambda token: token["prob"])


async def _play_until_ended(
    client,
    *,
    mode: str = "classic",
    model: str = "qwen",
    max_steps: int = 60,
) -> tuple[str, dict, int]:
    create = await client.post("/api/v1/session", json={"mode": mode, "model": model})
    assert create.status_code == 201
    payload = create.json()
    session_id = payload["session_id"]
    tokens = payload["next_tokens_food"]
    snake_length = payload["snake_length"] + 1

    for step_index in range(1, max_steps + 1):
        token = _pick_token(tokens, prefer_eos=step_index > 8)
        step = await client.post(
            "/api/v1/game/step",
            json={
                "session_id": session_id,
                "eaten_token_id": token["token_id"],
                "current_snake_length": snake_length,
            },
        )
        assert step.status_code == 200
        body = step.json()
        if body["game_status"] == "ENDED":
            return session_id, body, step_index
        assert len(body["next_tokens_food"]) == 4
        tokens = body["next_tokens_food"]
        snake_length += 1

    raise AssertionError(f"Game did not reach ENDED within {max_steps} steps")


@pytest.mark.asyncio
async def test_eos_step_returns_ended(client):
    session_id, body, _ = await _play_until_ended(client)
    assert body["game_status"] == "ENDED"
    assert body["next_tokens_food"] == []

    session = await client.get(f"/api/v1/session/{session_id}")
    assert session.status_code == 200
    assert session.json()["game_status"] == "ENDED"


@pytest.mark.asyncio
async def test_full_game_flow_to_ended(client):
    session_id, body, steps = await _play_until_ended(client, mode="classic", model="qwen")
    assert body["game_status"] == "ENDED"
    assert steps >= 2
    assert session_id


@pytest.mark.asyncio
async def test_full_game_flow_qing_mode(client):
    session_id, body, steps = await _play_until_ended(client, mode="qing", model="qwen")
    assert body["game_status"] == "ENDED"
    assert steps >= 2
    assert session_id


@pytest.mark.asyncio
async def test_leaderboard_after_full_game(client):
    session_id, _, _ = await _play_until_ended(client)
    session = await client.get(f"/api/v1/session/{session_id}")
    assert session.status_code == 200
    score = max(session.json().get("score", 1), 1)

    submit = await client.post(
        "/api/v1/leaderboard",
        json={
            "player_name": "E2E_Player",
            "score": max(score, 1),
            "session_id": session_id,
        },
    )
    assert submit.status_code == 204

    listing = await client.get("/api/v1/leaderboard")
    assert listing.status_code == 200
    entries = listing.json()["entries"]
    assert any(
        entry["player_name"] == "E2E_Player" and entry["session_id"] == session_id
        for entry in entries
    )
