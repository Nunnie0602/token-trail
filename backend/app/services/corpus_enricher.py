import re

from app.models.schemas import GameMode, TokenFood
from app.services.corpus import Corpus, CorpusNode

EOS_VARIANTS: dict[GameMode, list[str]] = {
    "classic": ["故事告一段落", "夜色歸於沉寂", "一切回歸日常", "黎明終於到來"],
    "qing": ["事畢闔門", "夜色歸寂", "伏枕而眠", "東方既白"],
}

STUB_MIN_DEPTH_FOR_EOS = 24
STUB_EOS_ONLY_DEPTH = 28


def is_terminal_token_id(token_id: str) -> bool:
    return token_id.startswith("EOS") or token_id.startswith("Q_EOS")


def resolve_stub_depth(token_id: str) -> int:
    match = re.search(r"_S(\d+)_\d+$", token_id)
    if not match:
        return 0
    return int(match.group(1)) + 1


def _build_eos_candidates(mode: GameMode, prefix: str) -> list[TokenFood]:
    probs = [0.4, 0.3, 0.2, 0.1]
    return [
        TokenFood(
            token_id=f"{prefix}_EOS{index + 1}",
            text=text,
            prob=probs[index],
            is_eos=True,
        )
        for index, text in enumerate(EOS_VARIANTS[mode])
    ]


def _build_continuation_candidates(
    mode: GameMode,
    token_id: str,
    text: str,
    depth: int,
) -> list[TokenFood]:
    anchor = text[:6] if len(text) > 6 else text
    if mode == "qing":
        templates = [
            (f"復又{anchor}", 0.4),
            ("俄而風起簾動", 0.3),
            ("忽覺聲息漸近", 0.2),
            ("遂見人影婆娑", 0.1),
        ]
    else:
        templates = [
            (f"你繼續面對{anchor}", 0.4),
            ("此刻氣氛更詭異", 0.3),
            ("忽然又起變化", 0.2),
            ("接下來你硬着頭皮上前", 0.1),
        ]

    return [
        TokenFood(
            token_id=f"{token_id}_S{depth}_{index}",
            text=template_text,
            prob=prob,
        )
        for index, (template_text, prob) in enumerate(templates)
    ]


def _create_stub_node(
    mode: GameMode,
    token_id: str,
    text: str,
    depth: int,
) -> CorpusNode:
    if depth >= STUB_EOS_ONLY_DEPTH:
        return CorpusNode(next=_build_eos_candidates(mode, token_id))

    continuations = _build_continuation_candidates(mode, token_id, text, depth)
    if depth >= STUB_MIN_DEPTH_FOR_EOS:
        eos = _build_eos_candidates(mode, token_id)[0]
        return CorpusNode(next=[*continuations[:3], eos])
    return CorpusNode(next=continuations)


def materialize_stub_node(corpus: Corpus, token_id: str) -> CorpusNode | None:
    if token_id in corpus.nodes:
        return corpus.nodes[token_id]

    for node in corpus.nodes.values():
        reference = next((t for t in node.next if t.token_id == token_id), None)
        if reference is None or reference.is_eos or is_terminal_token_id(reference.token_id):
            continue
        stub = _create_stub_node(
            corpus.mode,
            token_id,
            reference.text,
            resolve_stub_depth(token_id),
        )
        corpus.nodes[token_id] = stub
        return stub
    return None


def enrich_corpus(corpus: Corpus) -> Corpus:
    for node in list(corpus.nodes.values()):
        for token in node.next:
            if token.is_eos or is_terminal_token_id(token.token_id):
                continue
            if token.token_id not in corpus.nodes:
                corpus.nodes[token.token_id] = _create_stub_node(
                    corpus.mode,
                    token.token_id,
                    token.text,
                    0,
                )
    return corpus
