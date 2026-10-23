from app.models.schemas import TokenFood
from app.services.corpus import find_token
from app.services.session import PlayerSession
from app.services.token_resolver import is_runtime_token, register_dynamic_tokens, resolve_token


def test_is_runtime_token():
    assert is_runtime_token("INF_ABCD1234") is True
    assert is_runtime_token("FB_C01") is True
    assert is_runtime_token("C_L1A") is False


def test_resolve_token_prefers_dynamic_tokens():
    dynamic = {
        "INF_ABCD1234": TokenFood(token_id="INF_ABCD1234", text="夜深人靜", prob=0.5),
    }
    token = resolve_token("classic", "qwen", "INF_ABCD1234", dynamic_tokens=dynamic)
    assert token is not None
    assert token.text == "夜深人靜"
    assert find_token("classic", "qwen", "INF_ABCD1234") is None


def test_resolve_token_falls_back_to_corpus():
    token = resolve_token("classic", "qwen", "C_L1A")
    assert token is not None
    assert token.text == "聽見敲門"


def test_register_dynamic_tokens_stores_runtime_only():
    session = PlayerSession(
        session_id="s1",
        mode="classic",
        model="qwen",
        game_status="PLAYING",
        current_prompt="起",
        current_temperature=1.0,
        snake_length=1,
        current_node_id="C_L1A",
        score=0,
        step_history=[],
        updated_at="now",
    )
    register_dynamic_tokens(
        session,
        [
            TokenFood(token_id="INF_AAAA", text="打開門縫", prob=0.4),
            TokenFood(token_id="C_L2A", text="語料", prob=0.3),
            TokenFood(token_id="FB_C01", text="安全", prob=0.2),
        ],
    )
    assert "INF_AAAA" in session.dynamic_tokens
    assert "FB_C01" in session.dynamic_tokens
    assert "C_L2A" not in session.dynamic_tokens
