from app.models.schemas import TokenFood


def classify_token_source(tokens: list[TokenFood]) -> str:
    if not tokens:
        return "empty"
    token_id = tokens[0].token_id
    if token_id.startswith("INF_"):
        return "inference"
    if token_id.startswith(("C_", "Q_")):
        return "corpus"
    if token_id.startswith("FB_"):
        return "static"
    return "unknown"
