import re

CLASSIC_PHRASE_PATTERN = re.compile(
    r"^[\u4e00-\u9fff]{2,8}$"
)

INVALID_CLASSIC_PATTERN = re.compile(
    r"[{}\[\]\"'\\]|json|JSON|```"
)


def is_valid_classic_phrase(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned or INVALID_CLASSIC_PATTERN.search(cleaned):
        return False
    return CLASSIC_PHRASE_PATTERN.match(cleaned) is not None
