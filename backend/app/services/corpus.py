import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from app.models.schemas import GameMode, ModelProfile, TokenFood

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass
class CorpusNode:
    next: list[TokenFood]


@dataclass
class Corpus:
    mode: GameMode
    initial_tokens: list[dict[str, str]]
    nodes: dict[str, CorpusNode] = field(default_factory=dict)


def _load_json(name: str) -> dict[str, Any]:
    with (DATA_DIR / name).open(encoding="utf-8") as handle:
        return cast(dict[str, Any], json.load(handle))


def _parse_corpus(raw: dict[str, Any]) -> Corpus:
    nodes: dict[str, CorpusNode] = {}
    for node_id, node_data in raw["nodes"].items():
        tokens = [TokenFood.model_validate(token) for token in node_data["next"]]
        nodes[node_id] = CorpusNode(next=tokens)
    return Corpus(
        mode=raw["mode"],
        initial_tokens=raw["initial_tokens"],
        nodes=nodes,
    )


_CORPUS_CACHE: dict[GameMode, Corpus] = {}
_MODEL_PROFILES: dict[str, Any] | None = None


def load_corpus(mode: GameMode) -> Corpus:
    if mode not in _CORPUS_CACHE:
        filename = "classic.json" if mode == "classic" else "qing.json"
        corpus = _parse_corpus(_load_json(filename))
        from app.services.corpus_enricher import enrich_corpus

        _CORPUS_CACHE[mode] = enrich_corpus(corpus)
    return _CORPUS_CACHE[mode]


def load_model_profiles() -> dict[str, Any]:
    global _MODEL_PROFILES
    if _MODEL_PROFILES is None:
        _MODEL_PROFILES = _load_json("model-profiles.json")
    return _MODEL_PROFILES


def pick_initial_token(mode: GameMode) -> dict[str, str]:
    corpus = load_corpus(mode)
    return random.choice(corpus.initial_tokens)


def apply_model_overrides(
    tokens: list[TokenFood],
    mode: GameMode,
    model: ModelProfile,
) -> list[TokenFood]:
    if model != "gemini":
        return tokens
    overrides = load_model_profiles()["text_overrides"][mode]
    return [
        TokenFood(
            token_id=token.token_id,
            text=overrides.get(token.token_id, token.text),
            prob=token.prob,
            is_eos=token.is_eos,
        )
        for token in tokens
    ]


def get_next_tokens(
    mode: GameMode,
    model: ModelProfile,
    node_id: str,
) -> list[TokenFood] | None:
    from app.services.corpus_enricher import materialize_stub_node

    corpus = load_corpus(mode)
    node = materialize_stub_node(corpus, node_id) or corpus.nodes.get(node_id)
    if node is None:
        return None
    return apply_model_overrides(node.next, mode, model)


def find_token(
    mode: GameMode,
    model: ModelProfile,
    token_id: str,
) -> TokenFood | None:
    corpus = load_corpus(mode)
    for node in corpus.nodes.values():
        for token in node.next:
            if token.token_id == token_id:
                return apply_model_overrides([token], mode, model)[0]

    from app.services.corpus_enricher import materialize_stub_node

    stub = materialize_stub_node(corpus, token_id)
    if stub:
        for token in stub.next:
            if token.token_id == token_id:
                return apply_model_overrides([token], mode, model)[0]
    return None


def find_token_text(mode: GameMode, model: ModelProfile, token_id: str) -> str | None:
    token = find_token(mode, model, token_id)
    return token.text if token else None
