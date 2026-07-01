SESSION_KEY_PREFIX = "session:"
RESULT_KEY_PREFIX = "result:"
LEADERBOARD_KEY = "global:leaderboard"
SESSION_TTL_SECONDS = 1800
RESULT_TTL_SECONDS = 604800
CACHE_TTL_SECONDS = 1800


def session_key(session_id: str) -> str:
    return f"{SESSION_KEY_PREFIX}{session_id}"


def result_key(session_id: str) -> str:
    return f"{RESULT_KEY_PREFIX}{session_id}"


def prefetch_key(session_id: str, eaten_token_id: str) -> str:
    return f"prefetch:{session_id}:{eaten_token_id}"
