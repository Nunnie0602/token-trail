import classicCorpus from "../data/classic.json";
import qingCorpus from "../data/qing.json";
import modelProfiles from "../data/model-profiles.json";
import { enrichCorpus, materializeStubNode } from "./corpusEnricher";
import type {
  Corpus,
  GameMode,
  ModelProfile,
  ModelProfiles,
  TokenFood,
} from "../types/game";

const CORPUS_MAP: Record<GameMode, Corpus> = {
  classic: enrichCorpus(classicCorpus as Corpus),
  qing: enrichCorpus(qingCorpus as Corpus),
};

export function loadCorpus(mode: GameMode): Corpus {
  return CORPUS_MAP[mode];
}

export function loadModelProfiles(): ModelProfiles {
  return modelProfiles as ModelProfiles;
}

export function pickInitialToken(mode: GameMode): { token_id: string; text: string } {
  const corpus = loadCorpus(mode);
  const index = Math.floor(Math.random() * corpus.initial_tokens.length);
  return corpus.initial_tokens[index];
}

export function applyModelOverrides(
  tokens: TokenFood[],
  mode: GameMode,
  model: ModelProfile,
): TokenFood[] {
  const overrides =
    model === "gemini" ? loadModelProfiles().text_overrides[mode] : null;

  return tokens.map((token) => ({
    ...token,
    text: overrides?.[token.token_id] ?? token.text,
  }));
}

export function getNextTokens(
  mode: GameMode,
  model: ModelProfile,
  nodeId: string,
): TokenFood[] | null {
  const corpus = loadCorpus(mode);
  const node = materializeStubNode(corpus, nodeId) ?? corpus.nodes[nodeId];
  if (!node) {
    return null;
  }
  return applyModelOverrides(node.next, mode, model);
}

export function validateCorpus(mode: GameMode): boolean {
  const corpus = loadCorpus(mode);
  return Object.values(corpus.nodes).every((node) => node.next.length === 4);
}
