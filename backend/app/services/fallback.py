from app.core.logging import logger
from app.models.schemas import GameMode, ModelProfile, TokenFood
from app.services.corpus import find_token_text, get_next_tokens
from app.services.mock_llm import MockLLM

FALLBACK_SAFE_TOKENS: dict[GameMode, list[TokenFood]] = {
    "classic": [
        TokenFood(token_id="FB_C01", text="你深吸一口氣", prob=0.45),
        TokenFood(token_id="FB_C02", text="四周忽然安靜", prob=0.25),
        TokenFood(token_id="FB_C03", text="你決定繼續前行", prob=0.2),
        TokenFood(token_id="FB_C04", text="夜色更深了", prob=0.1),
    ],
    "qing": [
        TokenFood(token_id="FB_Q01", text="你屏息凝神", prob=0.45),
        TokenFood(token_id="FB_Q02", text="四下寂然無聲", prob=0.25),
        TokenFood(token_id="FB_Q03", text="你續步前行", prob=0.2),
        TokenFood(token_id="FB_Q04", text="夜色愈發深沉", prob=0.1),
    ],
}


class FallbackService:
    def __init__(self, mock_llm: MockLLM | None = None) -> None:
        self._mock_llm = mock_llm or MockLLM()

    async def resolve(
        self,
        *,
        session_id: str,
        trace_id: str,
        mode: GameMode,
        model: ModelProfile,
        eaten_token_id: str,
        use_sync_mock: bool = True,
    ) -> list[TokenFood]:
        if use_sync_mock:
            tokens = await self._mock_llm.predict_next_tokens(mode, model, eaten_token_id)
            if tokens:
                logger.info(
                    "fallback_mock_inference",
                    session_id=session_id,
                    trace_id=trace_id,
                    eaten_token_id=eaten_token_id,
                    source="mock_llm",
                )
                return tokens

        safe = list(FALLBACK_SAFE_TOKENS[mode])
        eaten_text = find_token_text(mode, model, eaten_token_id)
        if eaten_text:
            safe[0] = TokenFood(
                token_id=safe[0].token_id,
                text=f"{safe[0].text}，方才{eaten_text}",
                prob=safe[0].prob,
            )

        logger.warning(
            "fallback_static_corpus",
            session_id=session_id,
            trace_id=trace_id,
            eaten_token_id=eaten_token_id,
            source="static_safe",
        )
        return safe

    def corpus_tokens(
        self,
        mode: GameMode,
        model: ModelProfile,
        token_id: str,
    ) -> list[TokenFood] | None:
        return get_next_tokens(mode, model, token_id)
