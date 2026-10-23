import time
import uuid

import httpx

from app.ai.guided_processor import extract_candidates, to_token_foods
from app.ai.model_profiles import CANDIDATE_COUNT, build_generation_prompt, get_sampling_profile
from app.core.config import settings
from app.core.logging import logger
from app.models.schemas import GameMode, ModelProfile, TokenFood
from app.services.mock_llm import MockLLM


class OllamaClient:
    def __init__(self, host: str, *, timeout: float) -> None:
        self._host = host.rstrip("/")
        self._timeout = timeout

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._host}/api/tags")
                return response.status_code == 200
        except (httpx.HTTPError, OSError):
            return False

    async def generate(self, *, model: str, prompt: str, profile: ModelProfile) -> str:
        sampling = get_sampling_profile(profile)
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": sampling.temperature,
                "top_p": sampling.top_p,
                "num_predict": sampling.num_predict,
            },
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(f"{self._host}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            return str(data.get("response", ""))


class InferenceService:
    def __init__(
        self,
        ollama: OllamaClient | None = None,
        mock_llm: MockLLM | None = None,
    ) -> None:
        self._ollama = ollama or OllamaClient(
            settings.ollama_host,
            timeout=settings.inference_timeout_seconds,
        )
        self._mock_llm = mock_llm or MockLLM()

    async def predict_next_tokens(
        self,
        *,
        prompt: str,
        mode: GameMode,
        model: ModelProfile,
        corpus_token_id: str | None = None,
    ) -> list[TokenFood]:
        if settings.inference_enabled:
            tokens = await self._try_ollama(prompt=prompt, mode=mode, model=model)
            if tokens:
                return tokens

        if corpus_token_id:
            corpus_tokens = await self._mock_llm.predict_next_tokens(mode, model, corpus_token_id)
            if corpus_tokens:
                logger.info(
                    "inference_corpus_fallback",
                    mode=mode,
                    model=model,
                    corpus_token_id=corpus_token_id,
                )
                return corpus_tokens

        return self._synthetic_fallback(mode)

    async def _try_ollama(
        self,
        *,
        prompt: str,
        mode: GameMode,
        model: ModelProfile,
    ) -> list[TokenFood]:
        started = time.perf_counter()
        try:
            generation_prompt = build_generation_prompt(
                story_context=prompt,
                mode=mode,
                model=model,
            )
            raw = await self._ollama.generate(
                model=settings.ollama_model,
                prompt=generation_prompt,
                profile=model,
            )
            phrases = extract_candidates(raw, mode, limit=CANDIDATE_COUNT)
            if len(phrases) < CANDIDATE_COUNT:
                logger.warning(
                    "inference_insufficient_candidates",
                    mode=mode,
                    model=model,
                    received=len(phrases),
                )
                return []

            tokens = to_token_foods(phrases)
            inference_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "inference_completed",
                mode=mode,
                model=model,
                inference_ms=inference_ms,
                candidate_count=len(tokens),
            )
            return tokens
        except (httpx.HTTPError, OSError, httpx.TimeoutException) as exc:
            inference_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.warning(
                "inference_ollama_failed",
                mode=mode,
                model=model,
                inference_ms=inference_ms,
                error=str(exc),
            )
            return []

    def _synthetic_fallback(self, mode: GameMode) -> list[TokenFood]:
        safe_texts = {
            "classic": ["你深吸一口氣", "四周忽然安靜", "你決定繼續前行", "夜色更深了"],
            "qing": ["你屏息凝神", "四下寂然無聲", "你續步前行", "夜色愈發深沉"],
        }
        weights = [0.45, 0.25, 0.2, 0.1]
        texts = safe_texts[mode]
        return [
            TokenFood(
                token_id=f"FB_{uuid.uuid4().hex[:6].upper()}",
                text=text,
                prob=prob,
            )
            for text, prob in zip(texts, weights, strict=True)
        ]
