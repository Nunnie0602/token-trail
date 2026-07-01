import { applySlidingWindow } from "../engine/slidingWindow";
import {
  getNextTokens,
  pickInitialToken,
} from "./corpusLoader";
import type {
  GameMode,
  GameSession,
  GameStatus,
  ModelProfile,
  TokenFood,
} from "../types/game";

function createSessionId(): string {
  return crypto.randomUUID().slice(0, 13);
}

function deriveTemperature(prob: number): number {
  return Number((0.5 + (1 - prob) * 1.2).toFixed(2));
}

export function createGameSession(
  mode: GameMode,
  model: ModelProfile,
): GameSession {
  const initial = pickInitialToken(mode);
  const nextTokens = getNextTokens(mode, model, initial.token_id) ?? [];

  return {
    sessionId: createSessionId(),
    mode,
    model,
    status: "PLAYING",
    score: 0,
    contextTokens: [initial.text],
    storyPath: [initial.text],
    chosenProbs: [],
    temperatureHistory: [1.0],
    currentTemperature: 1.0,
    currentNodeId: initial.token_id,
    nextTokens,
  };
}

export type EatTokenResult = {
  session: GameSession;
  evictedToken: string | null;
  isEos: boolean;
  stepFailed?: boolean;
};

export function processTokenEaten(
  session: GameSession,
  eaten: TokenFood,
): EatTokenResult {
  const temperature = deriveTemperature(eaten.prob);
  const { items: contextTokens, evicted } = applySlidingWindow(
    session.contextTokens,
    eaten.text,
  );

  let storyPath = [...session.storyPath, eaten.text];
  if (evicted) {
    const evictedIndex = storyPath.indexOf(evicted);
    if (evictedIndex >= 0) {
      storyPath = storyPath.filter((_, index) => index !== evictedIndex);
    }
  }

  const isEos = Boolean(eaten.is_eos);
  const nextTokens = isEos
    ? []
    : getNextTokens(session.mode, session.model, eaten.token_id) ?? [];

  const status: GameStatus = isEos ? "ENDED" : "PLAYING";

  return {
    session: {
      ...session,
      status,
      score: session.score + Math.round(eaten.prob * 100),
      contextTokens,
      storyPath,
      chosenProbs: [...session.chosenProbs, eaten.prob],
      temperatureHistory: [...session.temperatureHistory, temperature],
      currentTemperature: temperature,
      currentNodeId: eaten.token_id,
      nextTokens,
    },
    evictedToken: evicted,
    isEos,
  };
}

export function markGameOver(session: GameSession): GameSession {
  return { ...session, status: "COLLISION_FAILED" };
}
