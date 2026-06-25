import { describe, expect, it } from "vitest";
import classicCorpus from "../src/data/classic.json";
import {
  applyModelOverrides,
  getNextTokens,
  loadCorpus,
  validateCorpus,
} from "../src/services/corpusLoader";
import { countResolvableMissingNodes } from "../src/services/corpusEnricher";
import type { Corpus } from "../src/types/game";

describe("corpusLoader", () => {
  it("P1-T07: classic corpus nodes each have four candidates", () => {
    expect(validateCorpus("classic")).toBe(true);
    const corpus = loadCorpus("classic");
    expect(corpus.initial_tokens.length).toBeGreaterThan(0);
    expect(Object.keys(corpus.nodes).length).toBeGreaterThan(15);
  });

  it("P1-T08: qing mode loads classical style corpus", () => {
    const corpus = loadCorpus("qing");
    expect(corpus.mode).toBe("qing");
    expect(corpus.nodes.Q_INIT_01.next[0].text).toMatch(/叩|門/);
    const geminiTokens = applyModelOverrides(
      corpus.nodes.Q_INIT_01.next,
      "qing",
      "gemini",
    );
    expect(geminiTokens[0].text).not.toBe(corpus.nodes.Q_INIT_01.next[0].text);
  });

  it("flags missing corpus nodes before enrichment", () => {
    expect(countResolvableMissingNodes(classicCorpus as Corpus)).toBeGreaterThan(
      0,
    );
  });

  it("P1-T16: corpus graph sustains at least 25 non-EOS rounds", () => {
    let nodeId = "INIT_01";
    for (let round = 0; round < 25; round += 1) {
      const next = getNextTokens("classic", "qwen", nodeId);
      expect(next).not.toBeNull();
      expect(next).toHaveLength(4);
      const eaten = next!.find((token) => !token.is_eos);
      expect(eaten).toBeDefined();
      nodeId = eaten!.token_id;
    }
  });

  it("returns cloned token arrays for stable React updates", () => {
    const first = getNextTokens("classic", "qwen", "INIT_01");
    const second = getNextTokens("classic", "qwen", "INIT_01");
    expect(first).not.toBe(second);
  });
});
