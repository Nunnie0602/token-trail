from app.models.schemas import GameMode, ModelProfile, TokenFood
from app.services.corpus import get_next_tokens


class MockLLM:
    """Phase 2 stand-in for Ollama; returns corpus-backed Top-4 distributions."""

    async def predict_next_tokens(
        self,
        mode: GameMode,
        model: ModelProfile,
        token_id: str,
    ) -> list[TokenFood]:
        tokens = get_next_tokens(mode, model, token_id)
        if tokens is None:
            return []
        return tokens[:4]
