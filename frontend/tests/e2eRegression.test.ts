import { describe, expect, it } from "vitest";
import { MAX_SNAKE_LENGTH } from "../src/engine/constants";
import { applyModelOverrides, getNextTokens } from "../src/services/corpusLoader";
import {
  createGameSession,
  processTokenEaten,
} from "../src/services/gameSimulator";
import { buildStoryText } from "../src/utils/storyBuilder";
import { decodePersonality } from "../src/utils/personalityDecoder";
import type { GameMode, GameSession, ModelProfile, TokenFood } from "../src/types/game";

function pickToken(tokens: TokenFood[], preferEos = false): TokenFood {
  if (preferEos) {
    const eos = tokens.find((token) => token.is_eos);
    if (eos) {
      return eos;
    }
  }
  const nonEos = tokens.filter((token) => !token.is_eos);
  if (nonEos.length === 0) {
    return tokens[0];
  }
  return nonEos.reduce((best, token) => (token.prob > best.prob ? token : best));
}

function playUntilEos(mode: GameMode, model: ModelProfile): GameSession {
  let session = createGameSession(mode, model);
  let guard = 0;

  while (session.status === "PLAYING" && guard < 60) {
    guard += 1;
    const token = pickToken(session.nextTokens, guard > 8);
    session = processTokenEaten(session, token).session;
  }

  return session;
}

function eatSyntheticTokens(count: number): GameSession {
  let session = createGameSession("classic", "qwen");

  for (let index = 0; index < count; index += 1) {
    expect(session.contextTokens.length).toBeLessThanOrEqual(MAX_SNAKE_LENGTH);
    const token: TokenFood = {
      token_id: `SYN_${index}`,
      text: `片段${index}`,
      prob: 0.5,
    };
    session = processTokenEaten(session, token).session;
  }

  return session;
}

describe("E2E regression (simulated)", () => {
  it("P1-T14: classic mode plays to EOS with PRD narrative and personality", () => {
    const session = playUntilEos("classic", "qwen");
    expect(session.status).toBe("ENDED");
    expect(session.storyPath.length).toBeGreaterThan(1);
    expect(session.chosenProbs.length).toBeGreaterThan(0);

    const story = buildStoryText(session.storyPath);
    expect(story).toMatch(/^[^，]+，.+?\.\.\.\.\.\.。$/);
    expect(story).not.toMatch(/在『/);

    const personality = decodePersonality(session.chosenProbs);
    expect(["Greedy Searcher", "Chaos Explorer", "Balanced Navigator"]).toContain(
      personality.type,
    );
  });

  it("P1-T15: qing mode plays to EOS with classical corpus", () => {
    const session = playUntilEos("qing", "qwen");
    expect(session.status).toBe("ENDED");
    expect(session.mode).toBe("qing");

    const story = buildStoryText(session.storyPath);
    expect(story.endsWith("......。")).toBe(true);
    expect(session.nextTokens).toHaveLength(0);
  });

  it("P1-T16: sliding window keeps context at 20 after eating 25 tokens", () => {
    const session = eatSyntheticTokens(25);
    expect(session.contextTokens).toHaveLength(MAX_SNAKE_LENGTH);
    expect(session.storyPath.length).toBeLessThanOrEqual(MAX_SNAKE_LENGTH + 1);
  });

  it("P1-T17: gemini overrides change L1-L3 candidate text", () => {
    const cases: Array<{ mode: GameMode; nodeId: string }> = [
      { mode: "classic", nodeId: "INIT_01" },
      { mode: "classic", nodeId: "C_L1A" },
      { mode: "classic", nodeId: "C_L2A" },
      { mode: "qing", nodeId: "Q_INIT_01" },
      { mode: "qing", nodeId: "Q_L1A" },
      { mode: "qing", nodeId: "Q_L2A" },
    ];

    for (const { mode, nodeId } of cases) {
      const qwenTokens = getNextTokens(mode, "qwen", nodeId);
      expect(qwenTokens).not.toBeNull();
      const geminiTokens = applyModelOverrides(qwenTokens!, mode, "gemini");
      expect(
        geminiTokens.some((token, index) => token.text !== qwenTokens![index].text),
      ).toBe(true);
    }
  });
});
