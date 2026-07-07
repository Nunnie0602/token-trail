import re

QING_PHRASE_PATTERN = re.compile(
    r"^[\u4e00-\u9fff]{2,8}$"
)

INVALID_QING_PATTERN = re.compile(
    r"[{}\[\]\"'\\]|json|JSON|```"
)

QING_STYLE_HINT = re.compile(r"[之乎者也焉哉矣爾汝其若乃]")


def is_valid_qing_phrase(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned or INVALID_QING_PATTERN.search(cleaned):
        return False
    if QING_PHRASE_PATTERN.match(cleaned) is None:
        return False
    return QING_STYLE_HINT.search(cleaned) is not None or len(cleaned) <= 4
