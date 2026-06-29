SESSION_KEY_PREFIX = "session:"
LEADERBOARD_KEY = "global:leaderboard"
SESSION_TTL_SECONDS = 1800
CACHE_TTL_SECONDS = 1800


def session_key(session_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}{session_id}"


def prefetch_key(session_id: str, eaten_token_id: str) -> str:
    return f"prefetch:{session_id}:{eaten_token_id}"
