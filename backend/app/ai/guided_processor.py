import re
import uuid
from collections.abc import Callable

from app.ai.grammars.classic import is_valid_classic_phrase
from app.ai.grammars.qing import is_valid_qing_phrase
from app.models.schemas import GameMode, TokenFood

_LINE_SPLIT = re.compile(r"[\n\r]+|(?<=[。！？；])")
_STRIP_PREFIX = re.compile(r"^[\d\.\-\*\u2022、\s]+")

_DEFAULT_RANK_WEIGHTS = [0.4, 0.28, 0.2, 0.12]


def normalize_probabilities(probs: list[float]) -> list[float]:
    total = sum(probs)
    if total <= 0:
        uniform = 1.0 / len(probs)
        return [round(uniform, 4) for _ in probs]
    return [round(p / total, 4) for p in probs]


def _clean_line(line: str) -> str:
    cleaned = _STRIP_PREFIX.sub("", line.strip())
    cleaned = re.sub(r"[。！？；，、：「」『』（）\(\)\[\]\"'{}]", "", cleaned)
    return cleaned.strip()


def _validator(mode: GameMode) -> Callable[[str], bool]:
    if mode == "qing":
        return is_valid_qing_phrase
    return is_valid_classic_phrase


def extract_candidates(raw_text: str, mode: GameMode, *, limit: int = 4) -> list[str]:
    validate = _validator(mode)
    seen: set[str] = set()
    candidates: list[str] = []

    for chunk in _LINE_SPLIT.split(raw_text):
        phrase = _clean_line(chunk)
        if not phrase or phrase in seen:
            continue
        if not validate(phrase):
            continue
        seen.add(phrase)
        candidates.append(phrase)
        if len(candidates) >= limit:
            break

    return candidates


def to_token_foods(
    phrases: list[str],
    *,
    rank_weights: list[float] | None = None,
) -> list[TokenFood]:
    weights = rank_weights or _DEFAULT_RANK_WEIGHTS[: len(phrases)]
    if len(weights) < len(phrases):
        weights = weights + [weights[-1]] * (len(phrases) - len(weights))
    probs = normalize_probabilities(weights[: len(phrases)])

    return [
        TokenFood(
            token_id=f"INF_{uuid.uuid4().hex[:8].upper()}",
            text=phrase,
            prob=prob,
        )
        for phrase, prob in zip(phrases, probs, strict=True)
    ]
