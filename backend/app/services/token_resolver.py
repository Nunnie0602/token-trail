from app.models.schemas import GameMode, ModelProfile, TokenFood
from app.services.corpus import find_token
from app.services.session import PlayerSession

_RUNTIME_PREFIXES = ("INF_", "FB_")


def is_runtime_token(token_id: str) -> bool:
    return token_id.startswith(_RUNTIME_PREFIXES)


def register_dynamic_tokens(session: PlayerSession, tokens: list[TokenFood]) -> None:
    for token in tokens:
        if is_runtime_token(token.token_id):
            session.dynamic_tokens[token.token_id] = token


def resolve_token(
    mode: GameMode,
    model: ModelProfile,
    token_id: str,
    *,
    dynamic_tokens: dict[str, TokenFood] | None = None,
) -> TokenFood | None:
    runtime = dynamic_tokens or {}
    if token_id in runtime:
        return runtime[token_id]
    return find_token(mode, model, token_id)
