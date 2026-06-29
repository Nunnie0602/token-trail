import { applySlidingWindow } from "../engine/slidingWindow";
import type { CreateSessionResponse } from "../api/gameApi";
import type {
  GameSession,
  GameStatus,
  ModelProfile,
  TokenFood,
} from "../types/game";

function deriveTemperature(prob: number): number {
  return Number((0.5 + (1 - prob) * 1.2).toFixed(2));
}

export function mapApiSessionToGameSession(
  api: CreateSessionResponse,
  model: ModelProfile,
): GameSession {
  const initialText = api.current_prompt;
  return {
    sessionId: api.session_id,
    mode: api.mode,
    model,
    status: api.game_status,
    score: 0,
    contextTokens: [initialText],
    storyPath: [initialText],
    chosenProbs: [],
    temperatureHistory: [api.current_temperature],
    currentTemperature: api.current_temperature,
    currentNodeId: api.current_node_id,
    nextTokens: api.next_tokens_food,
  };
}

export function applyStepResponse(
  session: GameSession,
  eaten: TokenFood,
  response: {
    game_status: GameStatus;
    current_temperature: number;
    next_tokens_food: TokenFood[];
  },
): GameSession {
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

  return {
    ...session,
    status: response.game_status,
    score: session.score + Math.round(eaten.prob * 100),
    contextTokens,
    storyPath,
    chosenProbs: [...session.chosenProbs, eaten.prob],
    temperatureHistory: [...session.temperatureHistory, temperature],
    currentTemperature: response.current_temperature,
    currentNodeId: eaten.token_id,
    nextTokens: response.next_tokens_food,
  };
}
