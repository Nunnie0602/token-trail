import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
from app.ai.grammars.classic import is_valid_classic_phrase
from app.ai.grammars.qing import is_valid_qing_phrase
from app.ai.guided_processor import extract_candidates, normalize_probabilities, to_token_foods
from app.ai.inference import InferenceService, OllamaClient
from app.ai.model_profiles import build_generation_prompt
from app.cache.branch_cache import BranchCache
from app.models.schemas import StepRecord
from app.services.decoding import (
    PROMPT_WINDOW_MAX_SEGMENTS,
    derive_speed_multiplier,
    derive_temperature,
    rebuild_sliding_prompt,
)
from app.services.fallback import FallbackService
from app.services.game_step import GameStepService
from app.services.prefetcher import PrefetchScheduler
from app.services.result import FinalizeService, ResultManager
from app.services.session import SessionManager


def test_classic_grammar_accepts_valid_phrase():
    assert is_valid_classic_phrase("聽見敲門") is True


def test_classic_grammar_rejects_json_fragment():
    assert is_valid_classic_phrase('{"json"}') is False


def test_qing_grammar_accepts_valid_phrase():
    assert is_valid_qing_phrase("聖旨下") is True


def test_probability_normalization_sums_to_one():
    probs = normalize_probabilities([1, 2, 3, 4])
    assert abs(sum(probs) - 1.0) < 0.01


def test_temperature_increases_on_low_probability():
    low = derive_temperature(0.1, current=1.0)
    high = derive_temperature(0.9, current=1.0)
    assert low > high


def test_speed_multiplier_scales_with_temperature():
    assert derive_speed_multiplier(1.5) > 1.0


def test_prompt_sliding_window_keeps_last_twenty_segments():
    history = [
        StepRecord(
            step_index=i,
            token_id=f"T{i}",
            text=f"段{i}",
            prob=0.5,
            temperature=1.0,
        )
        for i in range(1, 22)
    ]
    prompt = rebuild_sliding_prompt("起", history)
    assert prompt.count("段") == PROMPT_WINDOW_MAX_SEGMENTS


def test_profile_switch_changes_prompt_template():
    qwen = build_generation_prompt(story_context="雨夜", mode="classic", model="qwen")
    gemini = build_generation_prompt(story_context="雨夜", mode="classic", model="gemini")
    assert qwen != gemini


def test_extract_candidates_filters_invalid_lines():
    raw = "聽見敲門\n{json}\n打開門縫\n裝作沒聽見\n拿起掃把"
    phrases = extract_candidates(raw, "classic", limit=4)
    assert "聽見敲門" in phrases
    assert all("{" not in phrase for phrase in phrases)


def test_to_token_foods_assigns_probabilities():
    tokens = to_token_foods(["聽見敲門", "打開門縫", "裝作沒聽見", "拿起掃把"])
    assert len(tokens) == 4
    assert abs(sum(token.prob for token in tokens) - 1.0) < 0.01


@pytest.mark.asyncio
async def test_step_end_to_end_with_mock_ollama(fake_redis, monkeypatch):
    monkeypatch.setattr("app.ai.inference.settings.inference_enabled", True)

    ollama = AsyncMock(spec=OllamaClient)
    ollama.generate.return_value = "打開門縫\n裝作沒聽見\n拿起掃把\n開始直播"
    inference = InferenceService(ollama=ollama)

    sessions = SessionManager(fake_redis)
    session = await sessions.create("classic", "qwen")
    service = GameStepService(
        sessions=sessions,
        cache=BranchCache(fake_redis),
        fallback=FallbackService(inference),
        prefetcher=PrefetchScheduler(BranchCache(fake_redis), inference, enabled=False),
        finalize=FinalizeService(sessions, ResultManager(fake_redis)),
    )

    response, _ = await service.execute(
        session_id=session.session_id,
        eaten_token_id="C_L1A",
        current_snake_length=2,
        trace_id="mock-step",
    )
    assert response.game_status == "PLAYING"
    assert len(response.next_tokens_food) == 4
    assert response.next_tokens_food[0].text == "打開門縫"


@pytest.mark.asyncio
async def test_prefetch_batch_writes_four_cache_keys(fake_redis, monkeypatch):
    monkeypatch.setattr("app.ai.inference.settings.inference_enabled", True)

    ollama = AsyncMock(spec=OllamaClient)
    ollama.generate.return_value = "打開門縫\n裝作沒聽見\n拿起掃把\n開始直播"
    inference = InferenceService(ollama=ollama)
    cache = BranchCache(fake_redis)
    prefetcher = PrefetchScheduler(cache, inference)
    sessions = SessionManager(fake_redis)
    session = await sessions.create("classic", "qwen")
    branches = sessions.initial_next_tokens(session)

    await prefetcher.seed_branches(
        session_id=session.session_id,
        mode="classic",
        model="qwen",
        current_prompt=session.current_prompt,
        branch_tokens=branches,
    )
    await asyncio.sleep(0.05)

    hits = 0
    for branch in branches:
        if await cache.get(session.session_id, branch.token_id) is not None:
            hits += 1
    assert hits == 4


@pytest.mark.asyncio
async def test_inference_timeout_falls_back_to_corpus(fake_redis, monkeypatch):
    monkeypatch.setattr("app.ai.inference.settings.inference_enabled", True)

    ollama = AsyncMock(spec=OllamaClient)
    ollama.generate.side_effect = httpx.TimeoutException("inference timeout")
    inference = InferenceService(ollama=ollama)
    service = FallbackService(inference)

    tokens = await service.resolve(
        session_id="s1",
        trace_id="t-timeout",
        mode="classic",
        model="qwen",
        current_prompt="雨夜",
        eaten_token_id="C_L1A",
        eaten_text="聽見敲門",
    )
    assert len(tokens) == 4
    assert tokens[0].token_id.startswith("C_L2")


@pytest.mark.asyncio
async def test_ollama_unavailable_falls_back_to_corpus(fake_redis, monkeypatch):
    monkeypatch.setattr("app.ai.inference.settings.inference_enabled", True)

    ollama = AsyncMock(spec=OllamaClient)
    ollama.generate.side_effect = httpx.ConnectError("connection refused")
    inference = InferenceService(ollama=ollama)
    service = FallbackService(inference)

    tokens = await service.resolve(
        session_id="s1",
        trace_id="t-conn",
        mode="classic",
        model="qwen",
        current_prompt="雨夜",
        eaten_token_id="C_L1A",
        eaten_text="聽見敲門",
    )
    assert len(tokens) == 4
