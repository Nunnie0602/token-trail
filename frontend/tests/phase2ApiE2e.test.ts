import { beforeAll, describe, expect, it } from "vitest";
import {
  applyStepResponse,
  mapApiSessionToGameSession,
} from "../src/services/apiGameAdapter";
import { buildStoryText } from "../src/utils/storyBuilder";
import { decodePersonality } from "../src/utils/personalityDecoder";
import type { GameSession, TokenFood } from "../src/types/game";
import {
  e2eCreateSession,
  e2eGetLeaderboard,
  e2eHealthCheck,
  e2ePostGameStep,
  e2eSubmitLeaderboard,
  getE2eApiBase,
  isE2eApiAvailable,
  pickToken,
} from "./helpers/phase2ApiClient";

const describeE2e = isE2eApiAvailable() ? describe : describe.skip;

async function playApiGameUntilEnded(
  mode: "classic" | "qing",
  model: "qwen" | "gemini" = "qwen",
  maxSteps = 60,
): Promise<GameSession> {
  const apiSession = await e2eCreateSession(mode, model);
  let session = mapApiSessionToGameSession(apiSession, model);
  let snakeLength = session.contextTokens.length + 1;

  for (let stepIndex = 1; stepIndex <= maxSteps; stepIndex += 1) {
    const token = pickToken(session.nextTokens, stepIndex > 8);
    const step = await e2ePostGameStep({
      session_id: session.sessionId,
      eaten_token_id: token.token_id,
      current_snake_length: snakeLength,
    });
    session = applyStepResponse(session, token, step);
    snakeLength += 1;

    if (session.status === "ENDED") {
      return session;
    }
    expect(step.next_tokens_food).toHaveLength(4);
  }

  throw new Error(`API game did not reach ENDED within ${maxSteps} steps`);
}

describeE2e("Phase 2 API E2E", () => {
  beforeAll(async () => {
    const healthy = await e2eHealthCheck();
    if (!healthy) {
      throw new Error(
        `E2E backend unavailable at ${getE2eApiBase()}. Start docker compose or set E2E_API_BASE_URL.`,
      );
    }
  });

  it("P2-T22: classic mode plays to ENDED via live Step API", async () => {
    const session = await playApiGameUntilEnded("classic", "qwen");
    expect(session.status).toBe("ENDED");
    expect(session.storyPath.length).toBeGreaterThan(1);
    expect(session.chosenProbs.length).toBeGreaterThan(0);

    const story = buildStoryText(session.storyPath);
    expect(story).toMatch(/^[^，]+，.+?\.\.\.\.\.\.。$/);

    const personality = decodePersonality(session.chosenProbs);
    expect(["Greedy Searcher", "Chaos Explorer", "Balanced Navigator"]).toContain(
      personality.type,
    );
  });

  it("P2-T22: qing mode plays to ENDED via live Step API", async () => {
    const session = await playApiGameUntilEnded("qing", "qwen");
    expect(session.status).toBe("ENDED");
    expect(session.mode).toBe("qing");

    const story = buildStoryText(session.storyPath);
    expect(story.endsWith("......。")).toBe(true);
    expect(session.nextTokens).toHaveLength(0);
  });

  it("P2-T23: leaderboard submit after settlement is visible on GET", async () => {
    const session = await playApiGameUntilEnded("classic", "qwen");
    const playerName = `E2E_${Date.now().toString(36)}`;

    await e2eSubmitLeaderboard(playerName, session.score, session.sessionId);

    const listing = await e2eGetLeaderboard();
    const match = listing.entries.find(
      (entry) => entry.player_name === playerName && entry.session_id === session.sessionId,
    );
    expect(match).toBeDefined();
    expect(match?.score).toBe(session.score);
  });

  it("P2-T22: step responses expose cache_hit header contract", async () => {
    const apiSession = await e2eCreateSession("classic", "qwen");
    const firstToken = apiSession.next_tokens_food[0] as TokenFood;
    const step = await e2ePostGameStep({
      session_id: apiSession.session_id,
      eaten_token_id: firstToken.token_id,
      current_snake_length: apiSession.snake_length + 1,
    });
    expect(typeof step.cache_hit).toBe("boolean");
    expect(step.next_tokens_food).toHaveLength(4);
  });
});
