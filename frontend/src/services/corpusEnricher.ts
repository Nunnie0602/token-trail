import type { Corpus, CorpusNode, GameMode, TokenFood } from "../types/game";

const EOS_VARIANTS: Record<GameMode, string[]> = {
  classic: ["故事告一段落", "夜色歸於沉寂", "一切回歸日常", "黎明終於到來"],
  qing: ["事畢闔門", "夜色歸寂", "伏枕而眠", "東方既白"],
};

/** Stub 節點在達到此深度前不出現 EOS，確保 P1-T16 可連續吃滿 25 Token */
const STUB_MIN_DEPTH_FOR_EOS = 24;
const STUB_EOS_ONLY_DEPTH = 28;

function isTerminalTokenId(tokenId: string): boolean {
  return tokenId.startsWith("EOS") || tokenId.startsWith("Q_EOS");
}

export function resolveStubDepth(tokenId: string): number {
  const match = tokenId.match(/_S(\d+)_\d+$/);
  if (!match) {
    return 0;
  }
  return Number.parseInt(match[1], 10) + 1;
}

function buildEosCandidates(mode: GameMode, prefix: string): TokenFood[] {
  const probs = [0.4, 0.3, 0.2, 0.1];
  return EOS_VARIANTS[mode].map((text, index) => ({
    token_id: `${prefix}_EOS${index + 1}`,
    text,
    prob: probs[index],
    is_eos: true,
  }));
}

function buildContinuationCandidates(
  mode: GameMode,
  tokenId: string,
  text: string,
  depth: number,
): TokenFood[] {
  const anchor = text.length > 6 ? text.slice(0, 6) : text;
  const templates =
    mode === "qing"
      ? [
          { text: `復又${anchor}`, prob: 0.4 },
          { text: "俄而風起簾動", prob: 0.3 },
          { text: "忽覺聲息漸近", prob: 0.2 },
          { text: "遂見人影婆娑", prob: 0.1 },
        ]
      : [
          { text: `你繼續面對${anchor}`, prob: 0.4 },
          { text: "此刻氣氛更詭異", prob: 0.3 },
          { text: "忽然又起變化", prob: 0.2 },
          { text: "接下來你硬着頭皮上前", prob: 0.1 },
        ];

  return templates.map((template, index) => ({
    token_id: `${tokenId}_S${depth}_${index}`,
    text: template.text,
    prob: template.prob,
  }));
}

function createStubNode(
  mode: GameMode,
  tokenId: string,
  text: string,
  depth: number,
): CorpusNode {
  if (depth >= STUB_EOS_ONLY_DEPTH) {
    return { next: buildEosCandidates(mode, tokenId) };
  }

  const continuations = buildContinuationCandidates(mode, tokenId, text, depth);

  if (depth >= STUB_MIN_DEPTH_FOR_EOS) {
    return { next: [...continuations.slice(0, 3), buildEosCandidates(mode, tokenId)[0]] };
  }

  return { next: continuations };
}

export function materializeStubNode(
  corpus: Corpus,
  tokenId: string,
): CorpusNode | null {
  if (corpus.nodes[tokenId]) {
    return corpus.nodes[tokenId];
  }

  for (const node of Object.values(corpus.nodes)) {
    const reference = node.next.find((token) => token.token_id === tokenId);
    if (!reference || reference.is_eos || isTerminalTokenId(reference.token_id)) {
      continue;
    }

    const stub = createStubNode(
      corpus.mode,
      tokenId,
      reference.text,
      resolveStubDepth(tokenId),
    );
    corpus.nodes[tokenId] = stub;
    return stub;
  }

  return null;
}

export function enrichCorpus(corpus: Corpus): Corpus {
  const nodes: Record<string, CorpusNode> = { ...corpus.nodes };

  for (const node of Object.values(nodes)) {
    for (const token of node.next) {
      if (token.is_eos || isTerminalTokenId(token.token_id) || nodes[token.token_id]) {
        continue;
      }
      nodes[token.token_id] = createStubNode(
        corpus.mode,
        token.token_id,
        token.text,
        0,
      );
    }
  }

  return { ...corpus, nodes };
}

export function countResolvableMissingNodes(corpus: Corpus): number {
  const referenced = new Set<string>();

  for (const node of Object.values(corpus.nodes)) {
    for (const token of node.next) {
      if (!token.is_eos && !isTerminalTokenId(token.token_id)) {
        referenced.add(token.token_id);
      }
    }
  }

  return [...referenced].filter((tokenId) => !corpus.nodes[tokenId]).length;
}
